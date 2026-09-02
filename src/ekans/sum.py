"""Sum: a Semigroup wrapper combining values via addition."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from ekans.extractable import Extractable
from ekans.semigroup import Semigroup

_AddT = TypeVar("_AddT", bound="SupportsAdd")


class SupportsAdd(Protocol):
    """Structural bound: anything with a self-typed `__add__`."""

    def __add__(self: _AddT, other: _AddT) -> _AddT:
        """Add `self` and `other`, returning the same type."""
        ...


A = TypeVar("A", bound=SupportsAdd)


@dataclass(frozen=True, eq=False)
class Sum(Semigroup, Extractable[A], Generic[A]):
    """Wraps a value, combining two via `+`.

    Attributes:
        value: The wrapped value.
    """

    value: A

    def mappend(self, other: "Sum[A]") -> "Sum[A]":
        """Combine `self` with `other` by adding their wrapped values.

        Args:
            other: Another Sum wrapping a value of the same type.

        Returns:
            A new Sum wrapping `self.value + other.value`.
        """
        return Sum(value=self.value + other.value)

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Sum[A]") -> bool:  # type: ignore[override]
        """Compare against another Sum wrapping the same type.

        Args:
            other: Another Sum wrapping the same type of value.

        Returns:
            Whether the wrapped values are equal, or ``NotImplemented``
            if `other` isn't a Sum at all.
        """
        if not isinstance(other, Sum):
            return NotImplemented
        return bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)

    def extract(self) -> A:
        """Return the wrapped value.

        Returns:
            The wrapped value.
        """
        return self.value
