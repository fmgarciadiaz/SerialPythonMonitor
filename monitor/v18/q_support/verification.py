"""Source export and relay comparison for the V18 pair."""
import hashlib
from pathlib import Path, PurePosixPath
import zipfile
APP="/home/arduino/ArduinoApps/scope-v18"
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_export(path, expected, app=APP):
    """Validate CLI-exported ZIP bytes without extracting any archive member."""
    with zipfile.ZipFile(path) as archive:
        files = {}
        for info in archive.infolist():
            name = info.filename.rstrip('/')
            member = PurePosixPath(name)
            if member.is_absolute() or '..' in member.parts or '\\' in name:
                raise ValueError('Unsafe exported archive path')
            if info.is_dir():
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Source export symlink is not accepted')
            if name in files:
                raise ValueError('Duplicate exported source file')
            files[name] = hashlib.sha256(archive.read(info)).hexdigest()
    for prefix in ('', Path(app).name + '/'):
        normalized = {name[len(prefix):]: value for name, value in files.items() if name.startswith(prefix)}
        if len(normalized) == len(files) and normalized == expected:
            return dict(exact=True, sha256=digest(path), archive_prefix=prefix)
    raise ValueError('CLI source export differs from exact original source manifest')

def relay_configuration_equal(left,right):
    # Docker may enumerate equivalent bind mounts in a different order.
    return (left['Config']==right['Config'] and left['HostConfig']==right['HostConfig'] and
            sorted(left['Mounts'],key=lambda m:m['Destination'])==
            sorted(right['Mounts'],key=lambda m:m['Destination']))
