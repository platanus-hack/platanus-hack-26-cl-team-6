import numpy as np


def attention(q, k, v):
    """Causal scaled dot-product attention.

    q, k, v: float64 arrays of shape (B, H, T, D).
    Returns an array of shape (B, H, T, D) where query position i attends to
    key positions 0..i (inclusive) with softmax(q.k / sqrt(D)).
    """
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
