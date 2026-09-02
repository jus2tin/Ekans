"""Semigroup: types with an associative combining operation."""

from abc import abstractmethod
from typing import Self

from ekans.functional import Functional


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
