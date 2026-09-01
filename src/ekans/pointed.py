"""Pointed: constructing a fresh instance from a single raw value."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ekans.functional import Functional

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")


class Pointed(Functional, Generic[A_co]):
    """A container that can be built fresh from a single value.

    Concrete types implement `point` as a classmethod, overriding both
    the parameter and return type with their own precise shape (e.g.
    `Identity[A]` implements
    `point(cls, value: A) -> Identity[A]`). No free-function form —
    see docs/specs/pointed.md's Design section for why.
    """

    @classmethod
    @abstractmethod
    def point(cls, value: A) -> "Pointed[A]":
        """Construct a fresh instance wrapping `value`.

        Args:
            value: The value to wrap.

        Returns:
            A new Pointed instance wrapping `value`.
        """
        raise NotImplementedError
