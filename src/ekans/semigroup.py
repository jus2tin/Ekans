"""Semigroup: types with an associative combining operation."""

from abc import abstractmethod
from typing import Self, TypeVar, Union, overload

from ekans.const import Const
from ekans.functional import Functional
from ekans.identity import Identity

S = TypeVar("S", bound="Semigroup")
A = TypeVar("A")


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
def mappend(  # noqa: E302
    a: Union[Identity[S], Const[S, A]], b: Union[Identity[S], Const[S, A]]
) -> Union[Identity[S], Const[S, A]]:
    """Free-function form of pointwise `mappend` for Identity[S]/Const[S, A].

    Neither `Identity` nor `Const` nominally implements `Semigroup` --
    each is only a Semigroup when its held value is, a constraint
    Python can't express at the class level. This function expresses
    that constraint instead, via `S`'s bound:
    `mappend(Identity(value="a"), Identity(value="b"))` is a
    `mypy --strict` error, since `str` isn't a `Semigroup`.

    Args:
        a: The first Identity or Const, wrapping/holding a Semigroup value.
        b: The second Identity or Const, wrapping/holding a Semigroup value.

    Returns:
        A new Identity or Const (matching a's/b's shape) combining the
        held values via their own `mappend`.
    """
    if isinstance(a, Identity) and isinstance(b, Identity):
        return Identity(value=a.value.mappend(b.value))
    if isinstance(a, Const) and isinstance(b, Const):
        return Const(value=a.value.mappend(b.value))
    raise TypeError(f"mappend is not supported between {type(a)!r} and {type(b)!r}")
