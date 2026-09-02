"""Semigroup: types with an associative combining operation."""

from abc import abstractmethod
from typing import Self, TypeVar, Union, overload

from ekans.const import Const
from ekans.functional import Functional
from ekans.identity import Identity
from ekans.maybe import Just, Maybe, Nothing
from ekans.reader import Reader

S = TypeVar("S", bound="Semigroup")
A = TypeVar("A")
R = TypeVar("R")


class Semigroup(Functional):
    """A type with an associative binary operation, `mappend`.

    Unlike the Functor-based type classes, `Semigroup` describes plain
    values, not containers: `mappend` combines two values of the
    implementing type into a third value of the same type. Requires no
    override-narrowing in concrete subclasses -- `typing.Self` already
    expresses "returns exactly this class" precisely.
    """

    @abstractmethod
    def mappend(self, other: Self) -> Self:
        """Combine `self` with `other`.

        Must be associative:
        `a.mappend(b).mappend(c) == a.mappend(b.mappend(c))`.

        Args:
            other: Another value of the same type to combine with.

        Returns:
            The combination of `self` and `other`.
        """
        raise NotImplementedError


@overload
def mappend(a: Identity[S], b: Identity[S]) -> Identity[S]: ...
@overload
def mappend(a: Const[S, A], b: Const[S, A]) -> Const[S, A]: ...
@overload
def mappend(a: Reader[R, S], b: Reader[R, S]) -> Reader[R, S]: ...
@overload
def mappend(a: "Maybe[S]", b: "Maybe[S]") -> "Union[Just[S], Nothing[S]]": ...
def mappend(  # noqa: E302
    a: Union[Identity[S], Const[S, A], Reader[R, S], "Maybe[S]"],
    b: Union[Identity[S], Const[S, A], Reader[R, S], "Maybe[S]"],
) -> Union[Identity[S], Const[S, A], Reader[R, S], "Maybe[S]"]:
    """Free-function form of pointwise `mappend` for Identity/Const/Reader/Maybe.

    None of `Identity`, `Const`, `Reader`, nor `Maybe` nominally
    implements `Semigroup` -- each is only a Semigroup when its held
    (or, for Reader, produced) value is, a constraint Python can't
    express at the class level. This function expresses that
    constraint instead, via `S`'s bound: `mappend(Identity(value="a"),
    Identity(value="b"))` is a `mypy --strict` error, since `str`
    isn't a `Semigroup`.

    Args:
        a: The first Identity, Const, Reader, or Maybe, wrapping a
            Semigroup value.
        b: The second Identity, Const, Reader, or Maybe, wrapping a
            Semigroup value.

    Returns:
        A new value of the same shape as `a`/`b`, combining the held
        (or, for Reader, produced) values via their own `mappend`. For
        Reader specifically: `mappend(f, g).run(r) == f.run(r).mappend(g.run(r))`.
        For Maybe: `Nothing` combined with anything returns the other
        side unchanged; two `Just`s combine their held values.
    """
    if isinstance(a, Identity) and isinstance(b, Identity):
        return Identity(value=a.value.mappend(b.value))
    if isinstance(a, Const) and isinstance(b, Const):
        return Const(value=a.value.mappend(b.value))
    if isinstance(a, Reader) and isinstance(b, Reader):
        return Reader(run=lambda r: a.run(r).mappend(b.run(r)))
    if isinstance(a, Maybe) and isinstance(b, Maybe):
        match (a, b):
            case (Nothing(), _):
                return b
            case (_, Nothing()):
                return a
            case (Just(value=x), Just(value=y)):
                return Just(value=x.mappend(y))
            case _:
                # Same reasoning as maybe.py's own fallbacks -- mypy
                # can't prove the match over the abstract Maybe
                # parameter type is exhaustive.
                raise AssertionError("unreachable")
    raise TypeError(f"mappend is not supported between {type(a)!r} and {type(b)!r}")
