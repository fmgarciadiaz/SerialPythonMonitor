"""Exact private-app source/cache archives, runnable on Q without repo imports.

CLI mutations are confined to the explicit BatchArena app and a unique private
backup directory. Core helpers accept temporary directories for pure tests.
Archive extraction is manual: no path traversal, hardlinks or symlink parents.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile

APP = '/home/arduino/ArduinoApps/scope-v18'
WORK_PREFIX = '/home/arduino/.cache/serialmonitor/v18-production-'
PRODUCTION_APP = '/home/arduino/ArduinoApps/scope-v18'
PRODUCTION_WORK_PREFIX = '/home/arduino/.cache/serialmonitor/v18-production-'
PRODUCTION_ADDED = frozenset(('sketch/batch2_ownership.h', 'sketch/batch_command.h',
                              'sketch/spi16_geometry.h'))
EXCLUDED = {'.git', '.cache', '__pycache__', 'data', '.venv'}
EXTRA = 'archivoextra.yml'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or path.as_posix() != name
            or '..' in path.parts or '\\' in name or '\x00' in name):
        raise ValueError('Unsafe archive member: ' + repr(name))
    return name


def snapshot(root, kind):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Regular app root required')
    paths = [root] if kind == 'sources' else [root / '.cache']
    if kind not in ('sources', 'cache') or not paths[0].is_dir() or paths[0].is_symlink():
        raise ValueError('Regular source/cache tree required')
    paths.extend(sorted(paths[0].rglob('*')))
    records = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if kind == 'sources' and (any(part in EXCLUDED for part in path.relative_to(root).parts)
                or path.name == '.DS_Store' or path.suffix == '.pyc'):
            continue
        info = path.lstat()
        entry = dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid,
                     mtime_ns=info.st_mtime_ns)
        if stat.S_ISLNK(info.st_mode):
            if kind == 'sources':
                raise ValueError('Source symlink is not accepted')
            entry.update(kind='symlink', target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            entry['kind'] = 'directory'
        elif stat.S_ISREG(info.st_mode):
            entry.update(kind='file', size=info.st_size, sha256=digest(path))
        else:
            raise ValueError('Special file in source/cache tree: ' + relative)
        records[safe_name(relative)] = entry
    return records


def source_files(records):
    return {name: item['sha256'] for name, item in records.items() if item['kind'] == 'file'}


def pack(root, records, archive):
    # Explicit TarInfo prevents accidental hardlink optimizations and preserves
    # the exact metadata separately, including nanosecond mtimes.
    with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as out:
        for name, record in records.items():
            item = tarfile.TarInfo(name)
            for key in ('mode', 'uid', 'gid'):
                setattr(item, key, record[key])
            item.mtime = record['mtime_ns'] // 1000000000
            item.pax_headers['mtime'] = f"{item.mtime}.{record['mtime_ns'] % 1000000000:09d}"
            if record['kind'] == 'file':
                item.size = record['size']
                with (Path(root) / name).open('rb') as stream:
                    out.addfile(item, stream)
            else:
                item.type = tarfile.DIRTYPE if record['kind'] == 'directory' else tarfile.SYMTYPE
                if record['kind'] == 'symlink':
                    item.linkname = record['target']
                out.addfile(item)


def metadata(root, records):
    # Files first, directories deepest-first, root last: creation must not
    # invalidate a restored directory mtime. Do not follow cache symlinks.
    ordered = sorted(records, key=lambda n: (records[n]['kind'] == 'directory', -len(PurePosixPath(n).parts)))
    for name in ordered:
        path, item = Path(root) / name, records[name]
        current = path.lstat()
        if (current.st_uid, current.st_gid) != (item['uid'], item['gid']):
            os.chown(path, item['uid'], item['gid'], follow_symlinks=False)
        if item['kind'] != 'symlink':
            os.chmod(path, item['mode'])
        os.utime(path, ns=(current.st_atime_ns, item['mtime_ns']), follow_symlinks=False)


def unpack(archive, records, destination):
    destination = Path(destination)
    destination.mkdir()  # Must be a new owned staging directory.
    for name, record in records.items():
        safe_name(name)
        for parent in PurePosixPath(name).parents:
            if parent.as_posix() in records and records[parent.as_posix()]['kind'] != 'directory':
                raise ValueError('Archive path has a non-directory parent')
    with tarfile.open(archive, 'r:') as source:
        members = source.getmembers()
        if len(members) != len(records) or {m.name for m in members} != set(records):
            raise ValueError('Archive members differ from exact manifest')
        by_name = {m.name: m for m in members}
        for name in sorted(records, key=lambda n: (len(PurePosixPath(n).parts), n)):
            item, expected = by_name[name], records[name]
            path = destination / name
            if expected['kind'] == 'directory':
                if not item.isdir():
                    raise ValueError('Archive directory type changed')
                if name != '.':
                    path.mkdir()
            elif expected['kind'] == 'file':
                if not item.isfile() or item.size != expected['size']:
                    raise ValueError('Archive regular file changed')
                with source.extractfile(item) as stream, path.open('xb') as output:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        output.write(block)
                if digest(path) != expected['sha256']:
                    raise ValueError('Extracted file SHA256 differs')
            else:
                if not item.issym() or item.linkname != expected['target']:
                    raise ValueError('Archive symlink changed')
                os.symlink(item.linkname, path)
    metadata(destination, records)


def backup(root, folder):
    root, folder = Path(root), Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema=1, app=str(root), sources=snapshot(root, 'sources'), cache=snapshot(root, 'cache'))
    verification = {}
    for kind in ('sources', 'cache'):
        archive = folder / (kind + '.tar')
        pack(root, manifest[kind], archive)
        manifest[kind + '_tar_sha256'] = digest(archive)
        if snapshot(root, kind) != manifest[kind]:
            raise ValueError('Tree changed while archiving: ' + kind)
        # Demonstrate with this very ADB user's permissions that the complete
        # archive and its uid/gid/modes/links/mtime can be reconstructed BEFORE
        # any source mutation. A readable TAR alone does not establish that.
        stage = folder / ('verify_' + kind)
        unpack(archive, manifest[kind], stage)
        readback = snapshot(stage, kind)
        if readback != manifest[kind]:
            raise ValueError('Pre-mutation staging readback is not exact: ' + kind)
        proof = folder / ('verify_' + kind + '_manifest.json')
        proof.write_text(json.dumps(readback, indent=2) + '\n')
        verification[kind] = dict(exact=True, stage='verify_' + kind,
            archive_sha256=manifest[kind + '_tar_sha256'],
            manifest_sha256=digest(proof), entries=len(readback))
    manifest['staging_verification'] = verification
    path = folder / 'manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    return dict(manifest_sha256=digest(path), sources_tar_sha256=manifest['sources_tar_sha256'],
                cache_tar_sha256=manifest['cache_tar_sha256'], source_files=source_files(manifest['sources']),
                staging_verification=verification,
                metadata_fields=['mode', 'uid', 'gid', 'mtime_ns', 'type', 'symlink_target', 'file_sha256'])


def restore(root, folder, expected_manifest_sha256, allowed_added=None):
    root, folder = Path(root), Path(folder)
    path = folder / 'manifest.json'
    if digest(path) != expected_manifest_sha256:
        raise ValueError('Original archive manifest changed')
    manifest = json.loads(path.read_text())
    if manifest['app'] != str(root) or manifest['schema'] != 1:
        raise ValueError('Archive belongs to another app')
    current = source_files(snapshot(root, 'sources'))
    allowed_added = (set(PRODUCTION_ADDED) if str(root) == PRODUCTION_APP else {EXTRA}) if allowed_added is None else set(allowed_added)
    if str(root) == PRODUCTION_APP and allowed_added != set(PRODUCTION_ADDED):
        raise ValueError('Production source additions must match exact allowlist')
    unexpected = set(current) - set(source_files(manifest['sources'])) - allowed_added
    if unexpected:
        raise ValueError('Unowned new source files; no deletion attempted: ' + repr(sorted(unexpected)))
    for kind in ('sources', 'cache'):
        archive = folder / (kind + '.tar')
        if digest(archive) != manifest[kind + '_tar_sha256']:
            raise ValueError('Original archive changed: ' + kind)
        unpack(archive, manifest[kind], folder / ('restore_' + kind))
    # No application/relay start exists here. The caller starts only after
    # exact source/cache readback succeeds, including the original ELF/BIN.
    for name in allowed_added:
        safe_name(name)
        extra = root / name
        if extra.is_file() and not extra.is_symlink():
            extra.unlink()
        elif extra.exists() or extra.is_symlink():
            raise ValueError('Added source is not a regular file: ' + name)
    stage = folder / 'restore_sources'
    for name, record in manifest['sources'].items():
        if record['kind'] == 'directory':
            (root / name).mkdir(exist_ok=True)
        else:
            os.replace(stage / name, root / name)
    # Quarantine the mutated cache instead of deleting it. All paths are on
    # the same filesystem; rename errors leave archives for manual recovery.
    if (root / '.cache').exists():
        os.rename(root / '.cache', folder / 'mutated_cache')
    os.rename(folder / 'restore_cache/.cache', root / '.cache')
    metadata(root, manifest['sources'])
    exact_sources = snapshot(root, 'sources') == manifest['sources']
    exact_cache = snapshot(root, 'cache') == manifest['cache']
    if not exact_sources or not exact_cache:
        raise ValueError('Original source/cache readback is not exact')
    return dict(sources_exact=True, cache_exact=True,
                source_files=source_files(manifest['sources']), manifest_sha256=expected_manifest_sha256)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('snapshot', 'backup', 'restore'))
    parser.add_argument('--root', required=True)
    parser.add_argument('--folder')
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args(argv)
    if args.root not in (APP, PRODUCTION_APP) or Path(args.root).resolve() != Path(args.root):
        raise ValueError('Only explicit private or production V18 app roots are accepted')
    if args.action == 'snapshot':
        result = dict(source_files=source_files(snapshot(args.root, 'sources')),
                      cache=snapshot(args.root, 'cache'))
    else:
        prefix = WORK_PREFIX if args.root == APP else PRODUCTION_WORK_PREFIX
        if (not args.folder or not args.folder.startswith(prefix)
                or not re.fullmatch('[0-9a-f]{32}', args.folder[len(prefix):])):
            raise ValueError('Unique V18 backup folder required')
        if args.action == 'backup':
            result = backup(args.root, args.folder)
        else:
            result = restore(args.root, args.folder, args.manifest_sha256)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
