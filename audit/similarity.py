import numpy as np


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a, b = np.array(v1), np.array(v2)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


def response_similarity(answer1: str, answer2: str, embed_fn: callable) -> float:
    return cosine_similarity(embed_fn(answer1), embed_fn(answer2))
