"""Monad: a type that's both Applicative and Bind."""

from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from ekans.applicative import Applicative
from ekans.bind import Bind

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")


class Monad(Applicative[A_co], Bind[A_co], Generic[A_co]):
    """A type that's both `Applicative` (Pointed + Apply) and `Bind`.

    Concrete types implementing both `Applicative` and `Bind` should
    inherit `Monad` directly instead of listing `Applicative`/`Bind`
    (or `Pointed`/`Apply`) separately, which produces a contradictory
    MRO.
    """

    @abstractmethod
    def bind(  # type: ignore[override]
        self, f: Callable[[A_co], "Monad[B]"]
    ) -> "Monad[B]":
        """Apply `f` to the wrapped value(s), flattening the result.

        Narrows `Bind.bind`'s return type from `Bind[B]` to `Monad[B]`
        -- anything implementing `Monad` stays a `Monad` after `bind`,
        which the inherited `Bind` signature alone doesn't express.
        Purely a type-level narrowing (still abstract, no new
        behavior) -- concrete subclasses narrow it further to their
        own precise shape, same as `Apply.fmap`/`Applicative.ap`.

        Args:
            f: A function from the wrapped value to a new Monad of
                the same shape.

        Returns:
            The result of applying `f`, flattened into a single Monad
            of the same shape.
        """
        raise NotImplementedError
