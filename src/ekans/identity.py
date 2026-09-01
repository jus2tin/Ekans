"""The identity functor: a trivial wrapper around a single value."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from ekans.functional import Functional

A = TypeVar("A")


@dataclass(frozen=True)
class Identity(Functional, Generic[A]):
    """Wraps a single value without adding any structure.

    Attributes:
        value: The wrapped value.
    """

    value: A
