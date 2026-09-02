"""Applicative: a type that's both Pointed and Apply."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, overload

from ekans.apply import Apply
from ekans.pointed import Pointed

if TYPE_CHECKING:
    from ekans.identity import Identity
    from ekans.reader import Reader

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
R = TypeVar("R")


class Applicative(Pointed[A_co], Apply[A_co], Generic[A_co]):
    """A type that's both `Pointed` (can be built from a value via `point`)
    and `Apply` (can apply a wrapped function to itself via `ap`).

    No new abstract methods -- a pure composition of its two parents.
    Concrete types implementing both `Pointed` and `Apply` should
    inherit `Applicative` directly instead of listing `Pointed`/`Apply`
    (or `Functor`) separately, which produces a contradictory MRO.
    """

    @abstractmethod
    def fmap(self, f: Callable[[A_co], B]) -> "Applicative[B]":
        """Apply `f` to the wrapped value(s), preserving the container's shape.

        Narrows `Apply.fmap`'s return type from `Apply[B]` to
        `Applicative[B]` -- same reasoning `Apply` itself already
        applies to `Functor.fmap`: anything implementing `Applicative`
        stays an `Applicative` after `fmap`, which the inherited
        `Apply` signature alone doesn't express. Purely a type-level
        narrowing (still abstract, no new behavior).

        Args:
            f: The function to apply to the wrapped value(s).

        Returns:
            A new Applicative of the same shape, wrapping the mapped
            value(s).
        """
        raise NotImplementedError

    # mypy flags the parameter here as incompatible with Apply.ap's
    # supertype signature ([override]): narrowing the wrapper type
    # from Apply[...] to Applicative[...] is a contravariant-position
    # narrowing, same situation Identity.ap's own override is already
    # in -- the return type alone (like fmap above) doesn't trigger
    # this, only the parameter does.
    @abstractmethod
    def ap(  # type: ignore[override]
        self, f: "Applicative[Callable[[A_co], B]]"
    ) -> "Applicative[B]":
        """Apply the function wrapped in `f` to the value wrapped in `self`.

        Narrows `Apply.ap`'s parameter and return type from `Apply[...]`
        to `Applicative[...]`, same reasoning as `fmap` above.

        Args:
            f: A wrapped function to apply to the wrapped value.

        Returns:
            A new Applicative of the same shape, wrapping the result.
        """
        raise NotImplementedError


@overload
def liftA2(
    f: Callable[[A, B], C], fa: "Identity[A]", fb: "Identity[B]"
) -> "Identity[C]": ...
@overload  # noqa: E302
def liftA2(
    f: Callable[[A, B], C], fa: "Reader[R, A]", fb: "Reader[R, B]"
) -> "Reader[R, C]": ...
@overload  # noqa: E302
def liftA2(
    f: Callable[[A, B], C], fa: "Applicative[A]", fb: "Applicative[B]"
) -> "Applicative[C]": ...
def liftA2(  # noqa: E302
    f: Callable[[A, B], C], fa: "Applicative[A]", fb: "Applicative[B]"
) -> "Applicative[C]":
    """Lift a two-argument function into two Applicatives of the same shape.

    As each new concrete Applicative type is added, this gains its own
    `@overload` (above the loose `Applicative[A]`/`Applicative[B]`
    fallback, which must stay last) so calls against a known concrete
    type keep a precise return type -- same pattern `ap` uses in
    `apply.py`. Without the per-type overloads, this type-checks fine
    but silently degrades to the loose `Applicative[C]` even for a
    concrete `Identity`/`Reader` call.

    Args:
        f: A two-argument function to lift.
        fa: The first Applicative, wrapping `f`'s first argument.
        fb: The second Applicative, wrapping `f`'s second argument.

    Returns:
        A new Applicative of the same shape, wrapping `f` applied to
        both wrapped values.
    """
    return fb.ap(fa.fmap(lambda a: lambda b: f(a, b)))
