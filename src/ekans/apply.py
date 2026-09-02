"""Apply: applying a wrapped function to a wrapped value."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, overload

from ekans.functor import Functor

if TYPE_CHECKING:
    from ekans.identity import Identity
    from ekans.reader import Reader

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")
R = TypeVar("R")


class Apply(Functor[A_co], Generic[A_co]):
    """A Functor that can also apply a wrapped function to itself.

    Concrete types implement `ap`, overriding the parameter and
    return type with their own precise shape (e.g. `Identity[A]`
    implements `ap(self, f: Identity[Callable[[A], B]]) -> Identity[B]`).
    """

    @abstractmethod
    def fmap(self, f: Callable[[A_co], B]) -> "Apply[B]":
        """Apply `f` to the wrapped value(s), preserving the container's shape.

        Narrows `Functor.fmap`'s return type from `Functor[B]` to
        `Apply[B]` -- anything implementing `Apply` stays an `Apply`
        after `fmap`, which the inherited `Functor` signature alone
        doesn't express. Purely a type-level narrowing (still
        abstract, no new behavior) -- concrete subclasses narrow it
        further to their own precise shape, same as `Functor.fmap`.

        Args:
            f: The function to apply to the wrapped value(s).

        Returns:
            A new Apply of the same shape, wrapping the mapped value(s).
        """
        raise NotImplementedError

    @abstractmethod
    def ap(self, f: "Apply[Callable[[A_co], B]]") -> "Apply[B]":
        """Apply the function wrapped in `f` to the value wrapped in `self`.

        Args:
            f: A wrapped function to apply to the wrapped value.

        Returns:
            A new Apply of the same shape, wrapping the result.
        """
        raise NotImplementedError


@overload
def ap(f: "Identity[Callable[[A], B]]", x: "Identity[A]") -> "Identity[B]": ...
@overload
def ap(f: "Reader[R, Callable[[A], B]]", x: "Reader[R, A]") -> "Reader[R, B]": ...
@overload
def ap(f: "Apply[Callable[[A], B]]", x: Apply[A]) -> Apply[B]: ...
def ap(f: "Apply[Callable[[A], B]]", x: Apply[A]) -> Apply[B]:  # noqa: E302
    """Free-function form of `Apply.ap`; delegates to the method.

    As each new concrete Apply type is added, this gains its own
    `@overload` (above the loose `Apply[A]` fallback, which must stay
    last) so calls against a known concrete type keep a precise
    return type.

    Args:
        f: A wrapped function to apply.
        x: The wrapped value to apply it to.

    Returns:
        The result of `x.ap(f)`.
    """
    return x.ap(f)
