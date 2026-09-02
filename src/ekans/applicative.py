"""Applicative: a type that's both Pointed and Apply."""

from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from ekans.apply import Apply
from ekans.pointed import Pointed

A_co = TypeVar("A_co", covariant=True)
B = TypeVar("B")


class Applicative(Pointed[A_co], Apply[A_co], Generic[A_co]):
    """A type that's both `Pointed` (can be built from a value via `point`)
    and `Apply` (can apply a wrapped function to itself via `ap`).

    No new abstract methods -- a pure composition of its two parents.
    Concrete types implementing both `Pointed` and `Apply` should
    inherit `Applicative` directly instead of listing `Pointed`/`Apply`
    (or `Functor`) separately, which produces a contradictory MRO.
    """

    @abstractmethod
    def fmap(self, f: Callable[[A_co], B]) -> "Applicative[B]":
        """Apply `f` to the wrapped value(s), preserving the container's shape.

        Narrows `Apply.fmap`'s return type from `Apply[B]` to
        `Applicative[B]` -- same reasoning `Apply` itself already
        applies to `Functor.fmap`: anything implementing `Applicative`
        stays an `Applicative` after `fmap`, which the inherited
        `Apply` signature alone doesn't express. Purely a type-level
        narrowing (still abstract, no new behavior).

        Args:
            f: The function to apply to the wrapped value(s).

        Returns:
            A new Applicative of the same shape, wrapping the mapped
            value(s).
        """
        raise NotImplementedError

    # mypy flags the parameter here as incompatible with Apply.ap's
    # supertype signature ([override]): narrowing the wrapper type
    # from Apply[...] to Applicative[...] is a contravariant-position
    # narrowing, same situation Identity.ap's own override is already
    # in -- the return type alone (like fmap above) doesn't trigger
    # this, only the parameter does.
    @abstractmethod
    def ap(  # type: ignore[override]
        self, f: "Applicative[Callable[[A_co], B]]"
    ) -> "Applicative[B]":
        """Apply the function wrapped in `f` to the value wrapped in `self`.

        Narrows `Apply.ap`'s parameter and return type from `Apply[...]`
        to `Applicative[...]`, same reasoning as `fmap` above.

        Args:
            f: A wrapped function to apply to the wrapped value.

        Returns:
            A new Applicative of the same shape, wrapping the result.
        """
        raise NotImplementedError
