"""Pair related code."""

from __future__ import annotations


class Pair:
    """Pair object."""

    def __init__(self, base: str, quote: str) -> None:
        self.base = base
        self.quote = quote

    @classmethod
    def from_market(cls, market: str) -> Pair:
        """Create a pair from a Bitvavo market string such as ``BTC-EUR``."""
        base, _, quote = market.partition("-")
        return cls(base, quote)

    def __str__(self) -> str:
        return self.base + self.quote

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pair):
            return NotImplemented
        return (self.base, self.quote) == (other.base, other.quote)

    def __hash__(self) -> int:
        return hash((self.base, self.quote))
