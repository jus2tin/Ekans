"""The identity functor: a trivial wrapper around a single value."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Iterator, Type, TypeVar

from ekans.extractable import Extractable
from ekans.monad import Monad

if TYPE_CHECKING:
    from ekans.monoid import Monoid

A = TypeVar("A")
B = TypeVar("B")
S = TypeVar("S", bound="Monoid")


@dataclass(frozen=True, eq=False)
class Identity(Monad[A], Extractable[A], Generic[A]):
    """Wraps a single value without adding any structure.

    Attributes:
        value: The wrapped value.
    """

    value: A

    def fmap(self, f: Callable[[A], B]) -> "Identity[B]":
        """Apply `f` to the wrapped value.

        Args:
            f: The function to apply.

        Returns:
            A new Identity wrapping the result of `f(self.value)`.
        """
        return Identity(value=f(self.value))

    # mypy flags both the parameter and return type here as
    # incompatible with Pointed.point's supertype signature
    # ([override]): point's types are method-scoped TypeVars, not a
    # self-bound one, so mypy can't establish the substitutability it
    # can for instance methods like fmap -- narrowing here is the point.
    @classmethod
    def point(cls, value: A) -> "Identity[A]":  # type: ignore[override]
        """Construct an Identity wrapping `value`.

        Args:
            value: The value to wrap.

        Returns:
            A new Identity wrapping `value`.
        """
        return Identity(value=value)

    def ap(  # type: ignore[override]
        self, f: "Identity[Callable[[A], B]]"
    ) -> "Identity[B]":
        """Apply the function wrapped in `f` to the wrapped value.

        Args:
            f: An Identity wrapping the function to apply.

        Returns:
            A new Identity wrapping the result of `f.value(self.value)`.
        """
        return Identity(value=f.value(self.value))

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Identity[A]") -> bool:  # type: ignore[override]
        """Compare against another Identity wrapping the same type.

        Typed against ``Identity[A]`` rather than ``object`` so that mypy
        rejects comparisons between differently-parameterized Identity
        instances (e.g. ``Identity[int]`` vs. ``Identity[str]``) at
        type-check time, rather than silently returning False at runtime.

        Args:
            other: Another Identity wrapping the same type of value.

        Returns:
            Whether the wrapped values are equal, or ``NotImplemented``
            if `other` isn't an Identity at all.
        """
        if not isinstance(other, Identity):
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

    @classmethod
    def mempty(cls, value_type: Type[S]) -> "Identity[S]":
        """Construct the identity element for `value_type`, wrapped.

        Does not override `Monoid.mempty` -- `Identity` doesn't
        nominally inherit `Monoid`, same reasoning as its conditional
        `Semigroup` support (see `ekans.semigroup.mappend`). Unlike
        `mappend`, this works as a classmethod directly on `Identity`
        rather than needing a free function -- `S` here is a fresh,
        independently-bound TypeVar, not `Identity`'s own `A`, so it
        doesn't contaminate every `Identity[A]` instance the way a
        nominal instance method would have.

        Args:
            value_type: The concrete Monoid type to build the identity
                for.

        Returns:
            A new Identity wrapping `value_type.mempty()`.
        """
        return Identity(value=value_type.mempty())

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "Identity[B]"]
    ) -> "Identity[B]":
        """Apply `f` to the wrapped value, flattening the result.

        Args:
            f: A function from the wrapped value to a new Identity.

        Returns:
            The result of `f(self.value)`.
        """
        return f(self.value)

    def __iter__(self) -> Iterator[A]:
        """Yield the wrapped value.

        Returns:
            An iterator yielding exactly `self.value`.
        """
        yield self.value
