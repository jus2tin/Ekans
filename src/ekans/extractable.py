"""Extractable: containers that can hand back the single value they hold."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ekans.functional import Functional

A_co = TypeVar("A_co", covariant=True)


class Extractable(Functional, Generic[A_co]):
    """A container that can hand back the single value it holds.

    The dual of `Pointed`: where `point` builds a container from a
    value, `extract` pulls the value back out. Needs no override
    narrowing in concrete subclasses -- unlike `Pointed.point`/
    `Apply.ap`, `extract` only narrows a return type on an instance
    method, which mypy already handles precisely without help.
    """

    @abstractmethod
    def extract(self) -> A_co:
        """Return the single value this container holds.

        Returns:
            The held value.
        """
        raise NotImplementedError
