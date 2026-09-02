"""Semigroup: types with an associative combining operation."""

from abc import abstractmethod
from typing import Self, TypeVar

from ekans.functional import Functional
from ekans.identity import Identity

S = TypeVar("S", bound="Semigroup")


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


def mappend(a: Identity[S], b: Identity[S]) -> Identity[S]:
    """Free-function form of pointwise `mappend` for `Identity[S]`.

    `Identity[S]` doesn't nominally implement `Semigroup` -- it's only
    a Semigroup when `S` is, a constraint Python can't express at the
    class level. This function expresses that constraint instead, via
    `S`'s bound: `mappend(Identity(value="a"), Identity(value="b"))`
    is a `mypy --strict` error, since `str` isn't a `Semigroup`.

    Args:
        a: The first Identity, wrapping a Semigroup value.
        b: The second Identity, wrapping a Semigroup value.

    Returns:
        A new Identity wrapping `a.value.mappend(b.value)`.
    """
    return Identity(value=a.value.mappend(b.value))
