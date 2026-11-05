"""Finish every independent cleanup, then attempt guarded V20 rollback."""
def finish_steps(steps,restore,report,save):
    errors=[];report['trial_cleanup_active']=True
    try:
        for name,operation in steps:
            try:operation()
            except BaseException as exc:errors.append(dict(step=name,error=repr(exc)))
        try:restore(errors)
        except BaseException as exc:errors.append(dict(step='restore_v20',error=repr(exc)))
    finally:
        report['trial_cleanup_active']=False;report['trial_cleanup_errors']=errors;save()
    if errors:raise RuntimeError('V20 trial cleanup failed: '+repr(errors))


def app_is_stopped(backend,container):
    # Only a successful inventory proves absence; inspection/I/O errors propagate.
    names=backend._output('docker','ps','-a','--format','{{.Names}}').splitlines()
    return container not in names or not backend._inspect(container)['State']['Running']


def owned_relay(backend,container,token):
    names=backend._output('docker','ps','-a','--format','{{.Names}}').splitlines()
    if container not in names:return None
    info=backend._inspect(container)
    if (info.get('Config',{}).get('Labels') or {}).get('arduscopio.v20-trial')!=token:
        raise RuntimeError('Foreign V20 relay cannot be stopped')
    return info['Id']


def stop_relay_id(backend,board,identity,report):
    try:board.shell('docker','stop',identity)
    except Exception as exc:
        report.setdefault('cleanup_fallbacks',[]).append(dict(step='stop_relay',error=repr(exc)))
        board.shell('docker','kill',identity)
    if backend._inspect(identity)['State']['Running']:raise RuntimeError('V20 relay still running')


def confirm_quiescence(backend,quiet):
    backend._candidate_compile_cleared=all(quiet.values())
    if not backend._candidate_compile_cleared:raise RuntimeError('Private writers not confirmed stopped')
