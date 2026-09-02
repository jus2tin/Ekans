"""Monad: a type that's both Applicative and Bind."""

from typing import Generic, TypeVar

from ekans.applicative import Applicative
from ekans.bind import Bind

A_co = TypeVar("A_co", covariant=True)


class Monad(Applicative[A_co], Bind[A_co], Generic[A_co]):
    """A type that's both `Applicative` (Pointed + Apply) and `Bind`.

    No new abstract methods -- a pure composition of its two parents,
    same relationship `Applicative` already has to `Pointed`+`Apply`.
    Concrete types implementing both `Applicative` and `Bind` should
    inherit `Monad` directly instead of listing `Applicative`/`Bind`
    (or `Pointed`/`Apply`) separately, which produces a contradictory
    MRO.
    """
