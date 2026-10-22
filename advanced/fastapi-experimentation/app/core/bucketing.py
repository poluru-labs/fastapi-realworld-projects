import hashlib


def pick_variant_key(
    *,
    experiment_key: str,
    subject_id: str,
    variants: list[tuple[str, int]],
) -> str:
    """Deterministic weighted bucket. `variants` is (key, weight) in stable order."""
    digest = hashlib.sha256(f"{experiment_key}:{subject_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    cumulative = 0
    for key, weight in variants:
        cumulative += weight
        if bucket < cumulative:
            return key
    return variants[-1][0]
