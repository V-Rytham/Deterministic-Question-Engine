import hashlib


def stable_option_order(options: list[str], seed: str) -> list[str]:
    """Deterministic permutation of options (no RNG)."""
    return sorted(
        options,
        key=lambda o: hashlib.sha256(f"{seed}::{o}".encode("utf-8")).hexdigest(),
    )
