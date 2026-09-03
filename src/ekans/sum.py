"""Sum: a Semigroup wrapper combining values via addition."""

from dataclasses import dataclass
from typing import Generic, Iterator, Protocol, Type, TypeVar, Union, cast, overload

from ekans.extractable import Extractable
from ekans.semigroup import Semigroup

_AddT = TypeVar("_AddT", bound="SupportsAdd")
_ZeroT = TypeVar("_ZeroT", bound="SupportsZero")


class SupportsAdd(Protocol):
    """Structural bound: anything with a self-typed `__add__`."""

    def __add__(self: _AddT, other: _AddT) -> _AddT:
        """Add `self` and `other`, returning the same type."""
        ...


class SupportsZero(SupportsAdd, Protocol):
    """Structural bound: anything with a classmethod `zero()`."""

    @classmethod
    def zero(cls: Type[_ZeroT]) -> _ZeroT:
        """Return the additive identity for this type."""
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

    def __iter__(self) -> Iterator[A]:
        """Yield the wrapped value.

        Returns:
            An iterator yielding exactly `self.value`.
        """
        yield self.value

    @overload
    @classmethod
    def mempty(cls, value_type: Type[int]) -> "Sum[int]": ...
    @overload
    @classmethod
    def mempty(cls, value_type: Type[float]) -> "Sum[float]": ...
    @overload
    @classmethod
    def mempty(cls, value_type: Type[_ZeroT]) -> "Sum[_ZeroT]": ...
    @classmethod  # noqa: E301
    def mempty(
        cls, value_type: Union[Type[int], Type[float], Type[_ZeroT]]
    ) -> "Union[Sum[int], Sum[float], Sum[_ZeroT]]":
        """Construct the additive identity for `value_type`.

        Does not override `Monoid.mempty` -- `Sum` doesn't nominally
        inherit `Monoid` (a classmethod requiring an extra argument
        would be a genuine LSP violation against its zero-arg
        contract, verified directly). `int`/`float` are special-cased
        since they have no `.zero()` of their own; any other type
        must implement `SupportsZero`.

        Args:
            value_type: The concrete type to build the identity for --
                `int`, `float`, or any type implementing `SupportsZero`.

        Returns:
            A new Sum wrapping that type's additive identity.
        """
        if value_type is int:
            return Sum(value=0)
        if value_type is float:
            return Sum(value=0.0)
        # mypy can't narrow a `type[X] | type[Y] | type[TypeVar]` union via
        # `is` comparisons against the literal type items -- verified
        # directly (reproduced against a minimal probe under --strict); the
        # cast is a precise Type[_ZeroT], not Any.
        other = cast(Type[_ZeroT], value_type)
        return Sum(value=other.zero())
