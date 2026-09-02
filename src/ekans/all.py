"""All: a Semigroup wrapper combining booleans via logical AND."""

from dataclasses import dataclass

from ekans.extractable import Extractable
from ekans.monoid import Monoid


@dataclass(frozen=True, eq=False)
class All(Monoid, Extractable[bool]):
    """Wraps a bool, combining two via logical AND.

    Attributes:
        value: The wrapped boolean.
    """

    value: bool

    def mappend(self, other: "All") -> "All":
        """Combine `self` with `other` via logical AND.

        Args:
            other: Another All.

        Returns:
            A new All wrapping `self.value and other.value`.
        """
        return All(value=self.value and other.value)

    def __eq__(self, other: object) -> bool:
        """Compare against another All.

        Args:
            other: Any object.

        Returns:
            Whether `other` is an All wrapping an equal value.
        """
        return isinstance(other, All) and self.value == other.value

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)

    def extract(self) -> bool:
        """Return the wrapped boolean.

        Returns:
            The wrapped boolean.
        """
        return self.value

    @classmethod
    def mempty(cls) -> "All":
        """Construct the identity for logical AND.

        Returns:
            `All(value=True)` -- combining with `True` via AND leaves
            any value unchanged.
        """
        return All(value=True)
