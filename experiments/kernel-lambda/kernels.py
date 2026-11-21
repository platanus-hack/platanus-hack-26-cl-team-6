"""The v2 kernel suite: 8 ML kernels, each with a slow-but-reasonable baseline.

Each kernel has: baseline source (what agents see and are timed against),
an input generator, a fast float64 reference used only for correctness, and
a comparison. Agents submit one kernel per experiment; a team's score is the
sum over kernels of log2(speedup) of its best version of each.
"""

import numpy as np

BASELINES = {
    "attention": '''import numpy as np

def attention(q, k, v):
    """Causal softmax attention. q, k, v: (B, H, T, D) float64 -> (B, H, T, D)."""
    B, H, T, D = q.shape
    out = np.zeros_like(q)
    scale = 1.0 / np.sqrt(D)
    for b in range(B):
        for h in range(H):
            for i in range(T):
                s = k[b, h, : i + 1] @ q[b, h, i] * scale
                s = np.exp(s - s.max())
                out[b, h, i] = (s / s.sum()) @ v[b, h, : i + 1]
    return out
''',
    "layernorm": '''import numpy as np

def layernorm(x, gamma, beta):
    """Row-wise LayerNorm, eps=1e-5. x: (N, D); gamma, beta: (D,) -> (N, D)."""
    out = np.empty_like(x)
    for i in range(x.shape[0]):
        mu = x[i].mean()
        var = ((x[i] - mu) ** 2).mean()
        out[i] = (x[i] - mu) / np.sqrt(var + 1e-5) * gamma + beta
    return out
''',
    "xent": '''import numpy as np

def xent(logits, labels):
    """Mean softmax cross-entropy and its gradient.
    logits: (N, C) float64, labels: (N,) int64 -> (loss: float, grad: (N, C))."""
    N, C = logits.shape
    grad = np.empty_like(logits)
    loss = 0.0
    for i in range(N):
        z = logits[i] - logits[i].max()
        p = np.exp(z) / np.exp(z).sum()
        loss -= np.log(p[labels[i]])
        p[labels[i]] -= 1.0
        grad[i] = p / N
    return loss / N, grad
''',
    "conv1d": '''import numpy as np

def conv1d(x, w):
    """Causal depthwise 1-D convolution.
    x: (C, T), w: (C, K) -> y: (C, T) with y[c, t] = sum_j w[c, j] * x[c, t - j] (x = 0 for t < 0)."""
    C, T = x.shape
    K = w.shape[1]
    y = np.zeros_like(x)
    for c in range(C):
        for j in range(K):
            y[c, j:] += w[c, j] * x[c, : T - j]
    return y
''',
    "topk": '''import numpy as np

def topk(x, k=16):
    """Per-row top-k. x: (N, M) -> (values (N, k), indices (N, k)), sorted descending."""
    N = x.shape[0]
    vals = np.empty((N, k))
    idx = np.empty((N, k), dtype=np.int64)
    for i in range(N):
        order = np.argsort(x[i])[::-1][:k]
        idx[i] = order
        vals[i] = x[i, order]
    return vals, idx
''',
    "sqdist": '''import numpy as np

def sqdist(a, b):
    """Pairwise squared Euclidean distances. a: (N, D), b: (M, D) -> (N, M)."""
    out = np.empty((a.shape[0], b.shape[0]))
    for i in range(a.shape[0]):
        out[i] = ((a[i] - b) ** 2).sum(axis=1)
    return out
''',
    "segsum": '''import numpy as np

def segsum(values, seg, n_seg):
    """Unsorted segment sum. values: (L,) float64, seg: (L,) int64 in [0, n_seg) -> (n_seg,)."""
    out = np.zeros(n_seg)
    np.add.at(out, seg, values)
    return out
''',
    "ema": '''import numpy as np

def ema(x, a):
    """Per-row exponential moving average scan.
    x: (R, T), a: (R,) in (0, 1) -> y with y[:, 0] = x[:, 0], y[:, t] = a * y[:, t-1] + (1 - a) * x[:, t]."""
    y = np.empty_like(x)
    y[:, 0] = x[:, 0]
    for t in range(1, x.shape[1]):
        y[:, t] = a * y[:, t - 1] + (1 - a) * x[:, t]
    return y
''',
}


def _inputs(name, rng):
    n = rng.standard_normal
    if name == "attention":
        return tuple(n((1, 4, 512, 64)) for _ in range(3))
    if name == "layernorm":
        return n((8192, 256)), 1 + 0.1 * n(256), 0.1 * n(256)
    if name == "xent":
        return 3 * n((2048, 1000)), rng.integers(0, 1000, 2048)
    if name == "conv1d":
        return n((256, 4096)), n((256, 32)) / 8
    if name == "topk":
        return (n((4096, 1024)),)
    if name == "sqdist":
        return n((1024, 64)), n((1024, 64))
    if name == "segsum":
        L, S = 8_000_000, 200_000
        return n(L), rng.integers(0, S, L), S
    if name == "ema":
        return n((64, 8192)), rng.uniform(0.5, 0.99, 64)
    raise KeyError(name)


def make_inputs(name, seed):
    return _inputs(name, np.random.default_rng(seed))


# --- fast float64 references (correctness only) ---------------------------
def _ref_attention(q, k, v):
    T, D = q.shape[-2:]
    s = q @ np.swapaxes(k, -1, -2) / np.sqrt(D)
    s = np.where(np.tril(np.ones((T, T), bool)), s, -np.inf)
    s = np.exp(s - s.max(-1, keepdims=True))
    return (s / s.sum(-1, keepdims=True)) @ v


def _ref_layernorm(x, g, b):
    mu = x.mean(1, keepdims=True)
    return (x - mu) / np.sqrt(x.var(1, keepdims=True) + 1e-5) * g + b


def _ref_xent(z, y):
    z = z - z.max(1, keepdims=True)
    lse = np.log(np.exp(z).sum(1))
    N = len(y)
    p = np.exp(z - lse[:, None])
    p[np.arange(N), y] -= 1
    return float((lse - z[np.arange(N), y]).mean()), p / N


def _ref_conv1d(x, w):
    C, T = x.shape
    K = w.shape[1]
    y = np.zeros_like(x)
    for j in range(K):
        y[:, j:] += w[:, j : j + 1] * x[:, : T - j]
    return y


def _ref_topk(x, k=16):
    idx = np.argsort(-x, axis=1)[:, :k]
    return np.take_along_axis(x, idx, 1), idx


def _ref_sqdist(a, b):
    return ((a[:, None, :] - b[None]) ** 2).sum(-1) if a.shape[0] * b.shape[0] < 1e6 else (
        (a * a).sum(1)[:, None] - 2 * a @ b.T + (b * b).sum(1)[None])


def _ref_segsum(v, s, n):
    return np.bincount(s, weights=v, minlength=n)


def _ref_ema(x, a):
    y = np.empty_like(x)
    y[:, 0] = x[:, 0]
    for t in range(1, x.shape[1]):
        y[:, t] = a * y[:, t - 1] + (1 - a) * x[:, t]
    return y


REFERENCES = {
    "attention": _ref_attention, "layernorm": _ref_layernorm, "xent": _ref_xent,
    "conv1d": _ref_conv1d, "topk": _ref_topk, "sqdist": _ref_sqdist,
    "segsum": _ref_segsum, "ema": _ref_ema,
}


def _close(out, ref):
    out = np.asarray(out, dtype=np.float64)
    ref = np.asarray(ref, dtype=np.float64)
    if out.shape != ref.shape or not np.all(np.isfinite(out)):
        return False
    scale = float(np.abs(ref).max()) if ref.size else 1.0
    return bool(np.allclose(out, ref, rtol=1e-3, atol=1e-4 * max(scale, 1e-12)))


def check(name, inputs, out):
    ref = REFERENCES[name](*inputs)
    if name == "topk":
        x = inputs[0]
        try:
            vals, idx = out
            idx = np.asarray(idx).astype(np.int64)
        except Exception:
            return False
        return _close(vals, ref[0]) and idx.shape == ref[1].shape and _close(np.take_along_axis(x, idx, 1), ref[0])
    if name == "xent":
        try:
            loss, grad = out
        except Exception:
            return False
        return _close(np.float64(loss), ref[0]) and _close(grad, ref[1])
    return _close(out, ref)


KERNELS = list(BASELINES)
