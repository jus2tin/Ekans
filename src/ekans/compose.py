"""Compose: one functor nested inside another."""

from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterator, Protocol, TypeVar

from ekans.foldable import Foldable
from ekans.functor import Functor

A = TypeVar("A")
B = TypeVar("B")


class _FoldableFunctor(Foldable[Any], Protocol):
    """Structural bound for Compose's outer/inner wrapper: iterable and mappable.

    Private to this module -- not part of the public API. Declares
    `fmap`'s return type as `_FoldableFunctor` itself (not the looser
    `Functor[Any]` `Functor.fmap` declares) so `Compose.fmap`'s body,
    which feeds the outer `fmap` call's result straight back into a
    new `Compose`, type-checks without a cast -- verified directly.
    """

    def fmap(self, f: Callable[[Any], Any]) -> "_FoldableFunctor": ...


W = TypeVar("W", bound=_FoldableFunctor)


@dataclass(frozen=True, eq=False)
class Compose(Functor[A], Generic[W, A]):
    """One functor nested inside another (`Compose f g a = Compose (f (g a))`).

    Attributes:
        value: The outer functor, itself wrapping the inner functor,
            itself wrapping the innermost value(s) of type A.
    """

    value: W

    def fmap(self, f: Callable[[A], B]) -> "Compose[_FoldableFunctor, B]":
        """Map `f` over the innermost wrapped value(s), through both layers.

        Args:
            f: The function to apply to the innermost wrapped value(s).

        Returns:
            A new Compose of the same shape, wrapping the mapped value(s).
        """
        return Compose(value=self.value.fmap(lambda inner: inner.fmap(f)))

    def __iter__(self) -> Iterator[A]:
        """Yield the innermost wrapped value(s), flattening both layers.

        Returns:
            An iterator over every innermost value, outer-then-inner order.
        """
        for inner in self.value:
            yield from inner

    def __eq__(self, other: "Compose[W, A]") -> bool:  # type: ignore[override]
        """Compare against another Compose with the same W, A.

        Args:
            other: Another Compose with the same type parameters.

        Returns:
            Whether both wrap an equal value.
        """
        return isinstance(other, Compose) and self.value == other.value

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)
