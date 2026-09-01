"""The constant functor: holds a value, ignores the type it maps over."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.functor import Functor

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


@dataclass(frozen=True, eq=False)
class Const(Functor[B], Generic[A, B]):
    """Holds a value of type `A`, ignoring `B` entirely.

    Attributes:
        value: The held value.
    """

    value: A

    def fmap(self, f: Callable[[B], C]) -> "Const[A, C]":
        """Re-tag `B` as `C` without touching the held value.

        There's no `B` actually stored anywhere to apply `f` to -- `B`
        only ever exists at the type level -- so this is a no-op
        re-tag, not a real transformation.

        Args:
            f: Ignored.

        Returns:
            A new Const holding the same value, re-tagged to Const[A, C].
        """
        return Const(value=self.value)

    def __eq__(self, other: "Const[A, B]") -> bool:  # type: ignore[override]
        """Compare against another Const holding the same type of value.

        Typed against ``Const[A, B]`` rather than ``object`` so that
        mypy rejects comparisons between differently-parameterized
        Const instances in either type parameter, at type-check time.

        Args:
            other: Another Const with the same A and B.

        Returns:
            Whether the held values are equal, or ``NotImplemented``
            if `other` isn't a Const at all.
        """
        if not isinstance(other, Const):
            return NotImplemented
        return bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the held value.

        Returns:
            The hash of the held value.
        """
        return hash(self.value)
