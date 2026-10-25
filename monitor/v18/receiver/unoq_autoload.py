"""V18 installed-only connection compatibility entry."""
from monitor.v18.io.live_connection import installed_connection

def connect_scope(serial, progress=lambda text: None, running=lambda: True):
    return installed_connection(serial, progress, running)

def ensure_scope(serial, progress=lambda text: None, running=lambda: True, **options):
    from monitor.v18.io.live_connection import installed_identity
    if not running(): raise InterruptedError('Conexión cancelada')
    installed_identity(serial)
    progress('Scope V18 y relay verificados; sin reiniciar ni instalar')
    return 'v18'
