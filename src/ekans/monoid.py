"""Monoid: a Semigroup with an identity element, mempty."""

from abc import abstractmethod
from typing import Self

from ekans.semigroup import Semigroup


class Monoid(Semigroup):
    """A Semigroup with an identity element, `mempty`.

    `mempty` is `mappend`'s identity: combining any value with it,
    on either side, leaves the value unchanged.
    """

    @classmethod
    @abstractmethod
    def mempty(cls) -> Self:
        """Construct the identity element for this Monoid.

        Must satisfy, for any `x` of this type:
        `x.mempty().mappend(x) == x` and `x.mappend(x.mempty()) == x`.

        Returns:
            The identity element.
        """
        raise NotImplementedError
