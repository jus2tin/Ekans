"""Bind: chaining box-producing functions together."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, Union, overload

from ekans.apply import Apply
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


class Bind(Apply[A_co], Generic[A_co]):
    """An Apply that can chain box-producing functions together.

    Concrete types implement `bind`, overriding the parameter and
    return type with their own precise shape (e.g. `Identity[A]`
    implements `bind(self, f: Callable[[A], Identity[B]]) -> Identity[B]`).
    """

    @abstractmethod
    def bind(self, f: Callable[[A_co], "Bind[B]"]) -> "Bind[B]":
        """Apply `f` to the wrapped value(s), flattening the result.

        Unlike `fmap`, `f` itself returns a wrapped value -- `bind`
        doesn't leave a box of boxes behind, per the associativity
        law: `m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))`.

        Args:
            f: A function from the wrapped value to a new Bind of the
                same shape.

        Returns:
            The result of applying `f`, flattened into a single Bind
            of the same shape.
        """
        raise NotImplementedError


@overload
def bind(f: Callable[[A], "Identity[B]"], x: "Identity[A]") -> "Identity[B]": ...
@overload
def bind(f: Callable[[A], "Reader[R, B]"], x: "Reader[R, A]") -> "Reader[R, B]": ...
@overload  # noqa: E302
def bind(
    f: Callable[[A], "Maybe[B]"], x: "Just[A]"
) -> "Union[Just[B], Nothing[B]]": ...
@overload
def bind(f: Callable[[A], "Maybe[B]"], x: "Nothing[A]") -> "Nothing[B]": ...
@overload  # noqa: E302
def bind(
    f: Callable[[A], "Maybe[B]"], x: "Maybe[A]"
) -> "Union[Just[B], Nothing[B]]": ...
@overload  # noqa: E302
def bind(
    f: Callable[[A], "Either[L, B]"], x: "Right[L, A]"
) -> "Union[Left[L, B], Right[L, B]]": ...
@overload
def bind(f: Callable[[A], "Either[L, B]"], x: "Left[L, A]") -> "Left[L, B]": ...
@overload  # noqa: E302
def bind(
    f: Callable[[A], "Either[L, B]"], x: "Either[L, A]"
) -> "Union[Left[L, B], Right[L, B]]": ...
@overload
def bind(f: Callable[[A], "Tuple2[S, B]"], x: "Tuple2[S, A]") -> "Tuple2[S, B]": ...
@overload
def bind(f: Callable[[A], "Bind[B]"], x: "Bind[A]") -> "Bind[B]": ...
def bind(  # noqa: E302
    f: Union[Callable[[A], "Bind[B]"], Callable[[A], "Tuple2[S, B]"]],
    x: Union["Bind[A]", "Tuple2[S, A]"],
) -> Union["Bind[B]", "Tuple2[S, B]"]:
    """Free-function form of `Bind.bind`; delegates to the method.

    As each new concrete Bind type is added, this gains its own
    `@overload` (above the loose `Bind[A]` fallback, which must stay
    last) so calls against a known concrete type keep a precise
    return type -- same pattern `ap` uses in `apply.py`. `Tuple2` is
    the exception -- it has no `.bind()` method at all (nominal
    `Bind[B]` is impossible for it, per docs/specs/tuple2.md's Design
    section), so its branch combines both sides' held Semigroup
    values via `mappend` directly, genuinely applying `f` to the real
    second value first.

    Args:
        f: A function from the wrapped value to a new Bind (or, for
            `Tuple2`, a new `Tuple2`) of the same shape.
        x: The wrapped value to apply it to.

    Returns:
        The result of `x.bind(f)`, or, for `Tuple2`, the `mappend` of
        both sides' held first values, second set to `f`'s result.
    """
    if isinstance(x, Tuple2):
        assert callable(f)
        result = f(x.second)
        assert isinstance(result, Tuple2)
        return Tuple2(first=x.first.mappend(result.first), second=result.second)
    assert not isinstance(x, Tuple2)
    # f's static type is still the Union from the two branches above --
    # narrowing x away from Tuple2 doesn't narrow the independent `f`
    # parameter, since a Callable's return type can't be checked via
    # isinstance the way a value can. Safe here: only the Bind[A]
    # overload can reach this line with a real Callable[[A], Bind[B]].
    return x.bind(f)  # type: ignore[arg-type]
