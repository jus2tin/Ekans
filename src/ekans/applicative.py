"""Applicative: a type that's both Pointed and Apply."""

from typing import Generic, TypeVar

from ekans.apply import Apply
from ekans.pointed import Pointed

A_co = TypeVar("A_co", covariant=True)


class Applicative(Pointed[A_co], Apply[A_co], Generic[A_co]):
    """A type that's both `Pointed` (can be built from a value via `point`)
    and `Apply` (can apply a wrapped function to itself via `ap`).

    No new abstract methods -- a pure composition of its two parents.
    Concrete types implementing both `Pointed` and `Apply` should
    inherit `Applicative` directly instead of listing `Pointed`/`Apply`
    (or `Functor`) separately, which produces a contradictory MRO.
    """
