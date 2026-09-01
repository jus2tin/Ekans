"""Functor: mapping over a value without changing its container's shape."""

from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from ekans.functional import Functional

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")


class Functor(Functional, Generic[A_co]):
    """A container that can be mapped over without changing its shape.

    Concrete types implement `fmap`, overriding the return type with
    their own precise shape (e.g. `Identity[A]` implements
    `fmap(self, f: Callable[[A], B]) -> Identity[B]`).
    """

    @abstractmethod
    def fmap(self, f: Callable[[A_co], B]) -> "Functor[B]":
        """Apply `f` to the wrapped value(s), preserving the container's shape.

        Args:
            f: The function to apply to the wrapped value(s).

        Returns:
            A new Functor of the same shape, wrapping the mapped value(s).
        """
        raise NotImplementedError


def fmap(f: Callable[[A], B], functor: Functor[A]) -> Functor[B]:
    """Free-function form of `Functor.fmap`; delegates to the method.

    As concrete Functor types are added, this gains one `@overload` per
    type so calls against a known concrete type keep a precise return
    type (e.g. `Identity[B]` instead of the loose `Functor[B]` below).

    Args:
        f: The function to apply to the wrapped value(s).
        functor: The Functor instance to map over.

    Returns:
        The result of `functor.fmap(f)`.
    """
    return functor.fmap(f)
