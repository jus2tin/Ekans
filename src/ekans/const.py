"""The constant functor: holds a value, ignores the type it maps over."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Type, TypeVar

from ekans.extractable import Extractable
from ekans.functor import Functor

if TYPE_CHECKING:
    from ekans.monoid import Monoid

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
S = TypeVar("S", bound="Monoid")


@dataclass(frozen=True, eq=False)
class Const(Functor[B], Extractable[A], Generic[A, B]):
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

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
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

    def extract(self) -> A:
        """Return the held value.

        Returns:
            The held value.
        """
        return self.value

    @classmethod
    def point(cls, value_type: Type[S], value: B) -> "Const[S, B]":
        """Construct a Const wrapping `value_type`'s identity element.

        Mirrors `Const.mempty` exactly -- `value` is accepted purely
        for `Pointed.point`'s conventional shape, then unconditionally
        discarded (same precedent as `Const.fmap`'s unused `f`).
        There's no `A` value derivable from `value: B`, so
        `value_type.mempty()` is the only well-typed source for the
        result's held value.

        Args:
            value_type: The concrete Monoid type to build the
                identity for.
            value: Accepted for `Pointed.point`'s conventional shape;
                unused.

        Returns:
            A new Const holding `value_type.mempty()`.
        """
        return Const(value=value_type.mempty())

    @classmethod
    def mempty(cls, value_type: Type[S]) -> "Const[S, B]":
        """Construct the identity element for `value_type`, held.

        Does not override `Monoid.mempty` -- same non-nominal
        reasoning as `Identity.mempty`. `B` is freely inferred from
        context, unrelated to `S`, same as `Const.fmap`'s re-tagging.

        Args:
            value_type: The concrete Monoid type to build the identity
                for.

        Returns:
            A new Const holding `value_type.mempty()`.
        """
        return Const(value=value_type.mempty())
