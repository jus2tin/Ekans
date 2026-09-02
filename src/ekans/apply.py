"""Apply: applying a wrapped function to a wrapped value."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, Union, overload

from ekans.const import Const
from ekans.functor import Functor
from ekans.tuple2 import Tuple2

if TYPE_CHECKING:
    from ekans.either import Either, Left, Right
    from ekans.identity import Identity
    from ekans.maybe import Just, Maybe, Nothing
    from ekans.reader import Reader
    from ekans.semigroup import Semigroup

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")
R = TypeVar("R")
L = TypeVar("L")
S = TypeVar("S", bound="Semigroup")


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
def ap(f: "Const[S, Callable[[A], B]]", x: "Const[S, A]") -> "Const[S, B]": ...
@overload
def ap(f: "Maybe[Callable[[A], B]]", x: "Just[A]") -> "Union[Just[B], Nothing[B]]": ...
@overload
def ap(f: "Maybe[Callable[[A], B]]", x: "Nothing[A]") -> "Nothing[B]": ...
@overload
def ap(f: "Maybe[Callable[[A], B]]", x: "Maybe[A]") -> "Union[Just[B], Nothing[B]]": ...
@overload  # noqa: E302
def ap(
    f: "Either[L, Callable[[A], B]]", x: "Right[L, A]"
) -> "Union[Left[L, B], Right[L, B]]": ...
@overload
def ap(f: "Either[L, Callable[[A], B]]", x: "Left[L, A]") -> "Left[L, B]": ...
@overload  # noqa: E302
def ap(
    f: "Either[L, Callable[[A], B]]", x: "Either[L, A]"
) -> "Union[Left[L, B], Right[L, B]]": ...
@overload
def ap(f: "Tuple2[S, Callable[[A], B]]", x: "Tuple2[S, A]") -> "Tuple2[S, B]": ...
@overload
def ap(f: "Apply[Callable[[A], B]]", x: Apply[A]) -> Apply[B]: ...
def ap(  # noqa: E302
    f: Union[
        "Identity[Callable[[A], B]]",
        "Reader[R, Callable[[A], B]]",
        "Const[S, Callable[[A], B]]",
        "Maybe[Callable[[A], B]]",
        "Either[L, Callable[[A], B]]",
        "Tuple2[S, Callable[[A], B]]",
        "Apply[Callable[[A], B]]",
    ],
    x: Union[
        "Identity[A]",
        "Reader[R, A]",
        "Const[S, A]",
        "Maybe[A]",
        "Either[L, A]",
        "Tuple2[S, A]",
        Apply[A],
    ],
) -> Union[
    "Identity[B]",
    "Reader[R, B]",
    "Const[S, B]",
    "Maybe[B]",
    "Either[L, B]",
    "Tuple2[S, B]",
    Apply[B],
]:
    """Free-function form of `Apply.ap`; delegates to the method.

    As each new concrete Apply type is added, this gains its own
    `@overload` (above the loose `Apply[A]` fallback, which must stay
    last) so calls against a known concrete type keep a precise
    return type. `Const`/`Tuple2` are the exception -- neither has a
    `.ap()` method at all (nominal `Apply[B]` is impossible for either,
    per docs/specs/const-applicative.md's and docs/specs/tuple2.md's
    Design sections), so their branches combine both sides' held
    Semigroup values via `mappend` directly instead of delegating --
    unlike `Const`'s degenerate case, `Tuple2`'s branch also genuinely
    applies the wrapped function to a real second value.

    Args:
        f: A wrapped function to apply.
        x: The wrapped value to apply it to.

    Returns:
        The result of `x.ap(f)`, or, for `Const`/`Tuple2`, the
        `mappend` of both sides' held first values (plus, for
        `Tuple2`, the function genuinely applied to the second value).
    """
    if isinstance(f, Const) and isinstance(x, Const):
        return Const(value=x.value.mappend(f.value))
    if isinstance(f, Tuple2) and isinstance(x, Tuple2):
        return Tuple2(first=x.first.mappend(f.first), second=f.second(x.second))
    assert not isinstance(f, Const) and not isinstance(x, Const)
    assert not isinstance(f, Tuple2) and not isinstance(x, Tuple2)
    return x.ap(f)
