"""Product: a Semigroup wrapper combining values via multiplication."""

from dataclasses import dataclass
from typing import Generic, Iterator, Protocol, Type, TypeVar, Union, cast, overload

from ekans.extractable import Extractable
from ekans.semigroup import Semigroup

_MulT = TypeVar("_MulT", bound="SupportsMul")
_OneT = TypeVar("_OneT", bound="SupportsOne")


class SupportsMul(Protocol):
    """Structural bound: anything with a self-typed `__mul__`."""

    def __mul__(self: _MulT, other: _MulT) -> _MulT:
        """Multiply `self` and `other`, returning the same type."""
        ...


class SupportsOne(SupportsMul, Protocol):
    """Structural bound: anything with a classmethod `one()`."""

    @classmethod
    def one(cls: Type[_OneT]) -> _OneT:
        """Return the multiplicative identity for this type."""
        ...


M = TypeVar("M", bound=SupportsMul)


@dataclass(frozen=True, eq=False)
class Product(Semigroup, Extractable[M], Generic[M]):
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

    def extract(self) -> M:
        """Return the wrapped value.

        Returns:
            The wrapped value.
        """
        return self.value

    def __iter__(self) -> Iterator[M]:
        """Yield the wrapped value.

        Returns:
            An iterator yielding exactly `self.value`.
        """
        yield self.value

    @overload
    @classmethod
    def mempty(cls, value_type: Type[int]) -> "Product[int]": ...
    @overload
    @classmethod
    def mempty(cls, value_type: Type[float]) -> "Product[float]": ...
    @overload
    @classmethod
    def mempty(cls, value_type: Type[_OneT]) -> "Product[_OneT]": ...
    @classmethod  # noqa: E301
    def mempty(
        cls, value_type: Union[Type[int], Type[float], Type[_OneT]]
    ) -> "Union[Product[int], Product[float], Product[_OneT]]":
        """Construct the multiplicative identity for `value_type`.

        Does not override `Monoid.mempty` -- same non-nominal
        reasoning as `Sum.mempty`.

        Args:
            value_type: The concrete type to build the identity for --
                `int`, `float`, or any type implementing `SupportsOne`.

        Returns:
            A new Product wrapping that type's multiplicative identity.
        """
        if value_type is int:
            return Product(value=1)
        if value_type is float:
            return Product(value=1.0)
        # mypy can't narrow a `type[X] | type[Y] | type[TypeVar]` union via
        # `is` comparisons against the literal type items -- verified
        # directly (reproduced against a minimal probe under --strict); the
        # cast is a precise Type[_OneT], not Any.
        other = cast(Type[_OneT], value_type)
        return Product(value=other.one())
