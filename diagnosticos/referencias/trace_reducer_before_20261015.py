"""Exact drawing reducer before temporary-array optimization; benchmark reference."""
def _reduce_trace_for_display(x_data, y_data, xmin, xmax, pixels):
        """Reduce sólo el dibujo: primero, último y extremos de cada píxel.

        Mantiene el orden original (también los escalones con X repetida) y
        cada NaN que separa trazos. Las mediciones y el CSV usan datos completos.
        Al ampliar hasta pocos puntos por píxel se devuelve el trazo original.
        """
        if len(x_data) <= pixels * 4 or xmax <= xmin:
            return x_data, y_data
        x = np.asarray(x_data, dtype=float)
        y = np.asarray(y_data, dtype=float)
        finite = np.isfinite(x) & np.isfinite(y)
        delta = np.diff(x)
        if finite.all() and len(delta) and delta[0] > 0 and np.allclose(delta, delta[0], rtol=1e-9, atol=1e-9):
            # Uniform hardware samples: block extrema avoid per-point bucket
            # arrays and repeats. Each block is at most one display pixel wide.
            stride = max(1, math.ceil((xmax-xmin)/(pixels*delta[0])))
            stride = min(stride, len(x))
            blocks = len(x)//stride
            matrix = y[:blocks*stride].reshape(blocks, stride)
            starts = np.arange(blocks)*stride
            selected = np.concatenate((starts, starts+stride-1,
                starts+matrix.argmin(axis=1), starts+matrix.argmax(axis=1)))
            tail = blocks*stride
            if tail < len(x):
                selected = np.r_[selected, tail, len(x)-1, tail+y[tail:].argmin(), tail+y[tail:].argmax()]
            selected = np.unique(selected)
            return x[selected], y[selected]
        buckets = np.floor((np.where(finite, x, xmin) - xmin) * (pixels / (xmax - xmin)))
        # Cada valor no finito forma su propio grupo y conserva el corte.
        starts = np.r_[0, np.flatnonzero(
            (buckets[1:] != buckets[:-1]) | ~finite[1:] | ~finite[:-1]) + 1]
        ends = np.r_[starts[1:], len(x)]
        counts = ends - starts
        safe_y = np.where(finite, y, 0.0)
        lows = np.minimum.reduceat(safe_y, starts)
        highs = np.maximum.reduceat(safe_y, starts)
        indices = np.arange(len(x))
        low_indices = np.minimum.reduceat(
            np.where(safe_y == np.repeat(lows, counts), indices, len(x)), starts)
        high_indices = np.minimum.reduceat(
            np.where(safe_y == np.repeat(highs, counts), indices, len(x)), starts)
        selected = np.unique(np.concatenate((starts, ends - 1, low_indices, high_indices)))
        return x[selected], y[selected]
