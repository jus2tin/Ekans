"""Product: a Semigroup wrapper combining values via multiplication."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from ekans.semigroup import Semigroup

_MulT = TypeVar("_MulT", bound="SupportsMul")


class SupportsMul(Protocol):
    """Structural bound: anything with a self-typed `__mul__`."""

    def __mul__(self: _MulT, other: _MulT) -> _MulT:
        """Multiply `self` and `other`, returning the same type."""
        ...


M = TypeVar("M", bound=SupportsMul)


@dataclass(frozen=True, eq=False)
class Product(Semigroup, Generic[M]):
    """Wraps a value, combining two via `*`.

    Attributes:
        value: The wrapped value.
    """

    value: M

    def mappend(self, other: "Product[M]") -> "Product[M]":
        """Combine `self` with `other` by multiplying their wrapped values.

        Args:
            other: Another Product wrapping a value of the same type.

        Returns:
            A new Product wrapping `self.value * other.value`.
        """
        return Product(value=self.value * other.value)

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Product[M]") -> bool:  # type: ignore[override]
        """Compare against another Product wrapping the same type.

        Args:
            other: Another Product wrapping the same type of value.

        Returns:
            Whether the wrapped values are equal, or ``NotImplemented``
            if `other` isn't a Product at all.
        """
        if not isinstance(other, Product):
            return NotImplemented
        return bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)
