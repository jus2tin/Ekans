"""Apply: applying a wrapped function to a wrapped value."""

from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from ekans.functor import Functor

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")


class Apply(Functor[A_co], Generic[A_co]):
    """A Functor that can also apply a wrapped function to itself.

    Concrete types implement `ap`, overriding the parameter and
    return type with their own precise shape (e.g. `Identity[A]`
    implements `ap(self, f: Identity[Callable[[A], B]]) -> Identity[B]`).
    """

    @abstractmethod
    def ap(self, f: "Apply[Callable[[A_co], B]]") -> "Apply[B]":
        """Apply the function wrapped in `f` to the value wrapped in `self`.

        Args:
            f: A wrapped function to apply to the wrapped value.

        Returns:
            A new Apply of the same shape, wrapping the result.
        """
        raise NotImplementedError


def ap(f: "Apply[Callable[[A], B]]", x: Apply[A]) -> Apply[B]:
    """Free-function form of `Apply.ap`; delegates to the method.

    As each new concrete Apply type is added, this gains its own
    `@overload` (above a loose `Apply[A]` fallback) so calls against a
    known concrete type keep a precise return type -- ships as a
    single plain-typed function for now since only one signature
    exists until the first concrete type implements Apply (mypy
    requires 2+ variants for `@overload` to apply), same as `fmap`'s
    T-001 shape before Identity implemented Functor.

    Args:
        f: A wrapped function to apply.
        x: The wrapped value to apply it to.

    Returns:
        The result of `x.ap(f)`.
    """
    return x.ap(f)
