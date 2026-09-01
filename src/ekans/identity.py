"""The identity functor: a trivial wrapper around a single value."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.functor import Functor

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Identity(Functor[A], Generic[A]):
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
