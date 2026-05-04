"""
Unit tests for the Matula prime utilities (open_webui.utils.matula).

These tests are pure-Python and have no external dependencies.
"""

import pytest
from open_webui.utils.matula import (
    assign_matula_prime,
    is_prime,
    MemoryType,
    next_prime_after,
    nth_prime,
)


class TestIsPrime:
    def test_known_primes(self):
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        for p in primes:
            assert is_prime(p), f"{p} should be prime"

    def test_known_composites(self):
        composites = [0, 1, 4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 25]
        for c in composites:
            assert not is_prime(c), f"{c} should not be prime"

    def test_large_prime(self):
        # 7919 is the 1000th prime
        assert is_prime(7919)

    def test_large_composite(self):
        assert not is_prime(7920)


class TestNthPrime:
    def test_first_six_primes(self):
        expected = [2, 3, 5, 7, 11, 13]
        for i, p in enumerate(expected, start=1):
            assert nth_prime(i) == p

    def test_tenth_prime(self):
        assert nth_prime(10) == 29

    def test_invalid_n_raises(self):
        with pytest.raises(ValueError):
            nth_prime(0)
        with pytest.raises(ValueError):
            nth_prime(-1)


class TestNextPrimeAfter:
    def test_after_10(self):
        assert next_prime_after(10) == 11

    def test_after_prime(self):
        # After 13 the next prime is 17
        assert next_prime_after(13) == 17

    def test_after_1(self):
        assert next_prime_after(1) == 2

    def test_after_2(self):
        assert next_prime_after(2) == 3


class TestAssignMatulaPrime:
    def test_empty_set_returns_2(self):
        assert assign_matula_prime(set()) == 2

    def test_skips_used_primes(self):
        # 2, 3, 5 are taken → next available prime is 7
        assert assign_matula_prime({2, 3, 5}) == 7

    def test_fills_gaps(self):
        # 2 and 5 are taken but 3 is free → 3 is returned
        assert assign_matula_prime({2, 5}) == 3

    def test_sequential_assignment(self):
        used: set[int] = set()
        for i in range(1, 11):
            p = assign_matula_prime(used)
            assert is_prime(p)
            assert p not in used
            used.add(p)
        # After 10 sequential assignments the used set should contain the
        # first 10 primes: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29
        assert used == {2, 3, 5, 7, 11, 13, 17, 19, 23, 29}

    def test_ignores_non_prime_values_in_set(self):
        # assign_matula_prime should only look at primes in the set.
        # Non-prime entries are harmless; the first prime (2) should still
        # be returned when no primes are present.
        assert assign_matula_prime({4, 6, 8}) == 2


class TestMemoryType:
    def test_constants_defined(self):
        assert MemoryType.EPISODIC == "episodic"
        assert MemoryType.SEMANTIC == "semantic"
        assert MemoryType.PROCEDURAL == "procedural"
        assert MemoryType.SENSORY == "sensory"
        assert MemoryType.WORKING == "working"
        assert MemoryType.INTENTIONAL == "intentional"

    def test_six_types_in_all(self):
        assert len(MemoryType._ALL) == 6

    def test_is_valid_with_known_types(self):
        for t in MemoryType._ALL:
            assert MemoryType.is_valid(t)

    def test_is_valid_with_none(self):
        assert MemoryType.is_valid(None)

    def test_is_valid_rejects_unknown(self):
        assert not MemoryType.is_valid("unknown_type")
        assert not MemoryType.is_valid("")
