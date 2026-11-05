"""Stop a local preparation session, including children such as ADB."""
import os
import signal
import subprocess

def stop_process_tree(process):
    # Caller must create the child with start_new_session=True on POSIX.
    if os.name == 'posix':
        try: os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: pass
        # Descendants can remain even when the session leader already exited.
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    else:
        process.terminate()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: process.kill()
    process.wait(timeout=3)
