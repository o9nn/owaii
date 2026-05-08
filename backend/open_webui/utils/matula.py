"""
Matula prime utilities for memory atom eternal naming.

In Matula's correspondence, every rooted tree has a unique prime as its
"eternal name".  For memory atoms we use the simpler assignment rule:
the n-th memory atom (1-based) is assigned the n-th prime number.
This gives each atom a stable, collision-free integer identity that is
preserved under serialisation, database migrations, and vector-DB
round-trips.

The six memory subsystem types follow the regime-cognitive-ai schema:
  episodic    – specific events / experiences
  semantic    – general knowledge / facts
  procedural  – skills / how-to knowledge
  sensory     – raw perceptual / multimodal data
  working     – current-context / scratchpad
  intentional – future intentions / goals

References
----------
* Matula, D. W. (1968).  A natural rooted tree enumeration by prime
  factorization.  *SIAM Review*, 10(2), 273.
* Matula, D. W. (1978).  An integer representation for graphs.
  *Proc. 6th S-E Conf. Combinatorics*, 533–548.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Primality helpers (no external dependencies)
# ---------------------------------------------------------------------------

_PRIME_CACHE: list[int] = [2, 3, 5, 7, 11, 13]


def _extend_prime_cache(n: int) -> None:
    """Extend _PRIME_CACHE until it contains at least *n* primes."""
    candidate = _PRIME_CACHE[-1] + 2
    while len(_PRIME_CACHE) < n:
        if _is_prime_raw(candidate):
            _PRIME_CACHE.append(candidate)
        candidate += 2 if candidate > 2 else 1


def _is_prime_raw(n: int) -> bool:
    """Trial-division primality test (suitable for small n)."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    limit = int(n**0.5) + 1
    for d in range(3, limit, 2):
        if n % d == 0:
            return False
    return True


def is_prime(n: int) -> bool:
    """Return *True* if *n* is a prime number."""
    return _is_prime_raw(n)


def nth_prime(n: int) -> int:
    """Return the *n*-th prime (1-based).

    >>> nth_prime(1)
    2
    >>> nth_prime(6)
    13
    """
    if n < 1:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    _extend_prime_cache(n)
    return _PRIME_CACHE[n - 1]


def next_prime_after(value: int) -> int:
    """Return the smallest prime strictly greater than *value*.

    >>> next_prime_after(10)
    11
    >>> next_prime_after(13)
    17
    """
    candidate = value + 1
    while not _is_prime_raw(candidate):
        candidate += 1
    return candidate


def assign_matula_prime(existing_primes: set[int]) -> int:
    """Return the smallest prime not yet present in *existing_primes*.

    This is the canonical way to mint a new Matula prime for a memory atom:
    collect all primes already assigned to atoms in a user's memory space,
    then call this function to obtain the next unique eternal name.

    >>> assign_matula_prime(set())
    2
    >>> assign_matula_prime({2, 3, 5})
    7
    """
    candidate = 2
    while candidate in existing_primes:
        candidate = next_prime_after(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Six-memory subsystem type constants
# ---------------------------------------------------------------------------

class MemoryType:
    """Typed constants for the six cognitive memory subsystems."""

    EPISODIC: str = "episodic"
    """Specific autobiographical events and experiences."""

    SEMANTIC: str = "semantic"
    """General world knowledge, concepts, and facts."""

    PROCEDURAL: str = "procedural"
    """Skills, habits, and how-to knowledge."""

    SENSORY: str = "sensory"
    """Raw perceptual / multimodal input traces."""

    WORKING: str = "working"
    """Short-lived current-context scratchpad."""

    INTENTIONAL: str = "intentional"
    """Future intentions, goals, and prospective plans."""

    _ALL: tuple[str, ...] = (
        EPISODIC,
        SEMANTIC,
        PROCEDURAL,
        SENSORY,
        WORKING,
        INTENTIONAL,
    )

    @classmethod
    def is_valid(cls, value: Optional[str]) -> bool:
        """Return *True* if *value* is a recognised subsystem type (or *None*)."""
        return value is None or value in cls._ALL
