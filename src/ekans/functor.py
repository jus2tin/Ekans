"""Functor: mapping over a value without changing its container's shape."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, Union, overload

from ekans.functional import Functional

if TYPE_CHECKING:
    from ekans.const import Const
    from ekans.either import Either, Left, Right
    from ekans.identity import Identity
    from ekans.maybe import Just, Maybe, Nothing
    from ekans.reader import Reader
    from ekans.tuple2 import Tuple2

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")
H = TypeVar("H")
R = TypeVar("R")


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


@overload
def fmap(f: Callable[[A], B], functor: "Identity[A]") -> "Identity[B]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Const[H, A]") -> "Const[H, B]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Reader[R, A]") -> "Reader[R, B]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Just[A]") -> "Just[B]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Nothing[A]") -> "Nothing[B]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Maybe[A]") -> "Union[Just[B], Nothing[B]]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Left[H, A]") -> "Left[H, B]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Right[H, A]") -> "Right[H, B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Either[H, A]"
) -> "Union[Left[H, B], Right[H, B]]": ...
@overload
def fmap(f: Callable[[A], B], functor: "Tuple2[H, A]") -> "Tuple2[H, B]": ...
@overload
def fmap(f: Callable[[A], B], functor: Functor[A]) -> Functor[B]: ...
def fmap(f: Callable[[A], B], functor: Functor[A]) -> Functor[B]:  # noqa: E302
    """Free-function form of `Functor.fmap`; delegates to the method.

    As each new concrete Functor type is added, this gains its own
    `@overload` (above the loose `Functor[A]` fallback, which must stay
    last so mypy tries the precise overloads first) so calls against a
    known concrete type keep a precise return type.

    Args:
        f: The function to apply to the wrapped value(s).
        functor: The Functor instance to map over.

    Returns:
        The result of `functor.fmap(f)`.
    """
    return functor.fmap(f)
