"""Structured diagnostics for existing flow limits; no policy changes."""

class FlowLimitExceeded(RuntimeError):
    def __init__(self, scope, current, projected, limits, exceeded, *, peaks=None, context=None):
        self.details = dict(scope=scope, current=dict(current), projected=dict(projected),
                            limits=dict(limits), exceeded=list(exceeded),
                            peaks=dict(peaks or {}), context=dict(context or {}))
        names = {'samples': 'muestras', 'seconds': 'segundos', 'bytes': 'bytes',
                 'batches': 'lotes', 'controls': 'confirmaciones'}
        values = ', '.join(f'{names.get(key,key)} {projected[key]:g}/{limits[key]:g}'
                           for key in exceeded)
        super().__init__(f'{scope} atrasado: presupuesto excedido ({values}); '
                         'adquisición detenida sin descartar datos.')
