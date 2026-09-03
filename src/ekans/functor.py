"""Functor: mapping over a value without changing its container's shape."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, Union, overload

from ekans.functional import Functional

if TYPE_CHECKING:
    from ekans.compose import Compose
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
H2 = TypeVar("H2")
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
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Just[A]], A]"
) -> "Compose[Identity[Just[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Right[H, A]], A]"
) -> "Compose[Identity[Right[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Just[A]], A]"
) -> "Compose[Const[H, Just[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Right[H2, A]], A]"
) -> "Compose[Const[H, Right[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Just[Identity[A]], A]"
) -> "Compose[Just[Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Just[Const[H, A]], A]"
) -> "Compose[Just[Const[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Just[Just[A]], A]"
) -> "Compose[Just[Just[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Just[Right[H, A]], A]"
) -> "Compose[Just[Right[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Just[Tuple2[H, A]], A]"
) -> "Compose[Just[Tuple2[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Right[H, Identity[A]], A]"
) -> "Compose[Right[H, Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Right[H, Const[H2, A]], A]"
) -> "Compose[Right[H, Const[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Right[H, Just[A]], A]"
) -> "Compose[Right[H, Just[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Right[H, Right[H2, A]], A]"
) -> "Compose[Right[H, Right[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Right[H, Tuple2[H2, A]], A]"
) -> "Compose[Right[H, Tuple2[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Just[A]], A]"
) -> "Compose[Tuple2[H, Just[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Right[H2, A]], A]"
) -> "Compose[Tuple2[H, Right[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Identity[A]], A]"
) -> "Compose[Identity[Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Const[H, A]], A]"
) -> "Compose[Identity[Const[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Maybe[A]], A]"
) -> "Compose[Identity[Maybe[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Either[H, A]], A]"
) -> "Compose[Identity[Either[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Identity[Tuple2[H, A]], A]"
) -> "Compose[Identity[Tuple2[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Identity[A]], A]"
) -> "Compose[Const[H, Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Const[H2, A]], A]"
) -> "Compose[Const[H, Const[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Maybe[A]], A]"
) -> "Compose[Const[H, Maybe[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Either[H2, A]], A]"
) -> "Compose[Const[H, Either[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Const[H, Tuple2[H2, A]], A]"
) -> "Compose[Const[H, Tuple2[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Maybe[Identity[A]], A]"
) -> "Compose[Maybe[Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Maybe[Const[H, A]], A]"
) -> "Compose[Maybe[Const[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Maybe[Maybe[A]], A]"
) -> "Compose[Maybe[Maybe[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Maybe[Either[H, A]], A]"
) -> "Compose[Maybe[Either[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Maybe[Tuple2[H, A]], A]"
) -> "Compose[Maybe[Tuple2[H, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Either[H, Identity[A]], A]"
) -> "Compose[Either[H, Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Either[H, Const[H2, A]], A]"
) -> "Compose[Either[H, Const[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Either[H, Maybe[A]], A]"
) -> "Compose[Either[H, Maybe[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Either[H, Either[H2, A]], A]"
) -> "Compose[Either[H, Either[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Either[H, Tuple2[H2, A]], A]"
) -> "Compose[Either[H, Tuple2[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Identity[A]], A]"
) -> "Compose[Tuple2[H, Identity[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Const[H2, A]], A]"
) -> "Compose[Tuple2[H, Const[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Maybe[A]], A]"
) -> "Compose[Tuple2[H, Maybe[B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Either[H2, A]], A]"
) -> "Compose[Tuple2[H, Either[H2, B]], B]": ...
@overload  # noqa: E302
def fmap(
    f: Callable[[A], B], functor: "Compose[Tuple2[H, Tuple2[H2, A]], A]"
) -> "Compose[Tuple2[H, Tuple2[H2, B]], B]": ...
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
