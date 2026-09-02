"""All: a Semigroup wrapper combining booleans via logical AND."""

from dataclasses import dataclass

from ekans.semigroup import Semigroup


@dataclass(frozen=True, eq=False)
class All(Semigroup):
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
