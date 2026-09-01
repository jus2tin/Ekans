"""The root of Ekans' functional type-class hierarchy."""

import abc
from typing import Any, NoReturn


class Functional(abc.ABC):
    """Marks a type as immutable.

    Subclasses should be declared as ``@dataclass(frozen=True)``. A frozen
    dataclass's generated ``__init__`` assigns fields via
    ``object.__setattr__`` internally, so construction still works even
    though this class refuses every attribute assignment and deletion.
    """

    def __setattr__(self, name: str, value: Any) -> NoReturn:
        """Refuse to set an attribute.

        Args:
            name: The attribute name that mutation was attempted on.
            value: The value that mutation was attempted with.

        Raises:
            AttributeError: Always.
        """
        raise AttributeError(f"{type(self).__name__} is immutable: cannot set {name!r}")

    def __delattr__(self, name: str) -> NoReturn:
        """Refuse to delete an attribute.

        Args:
            name: The attribute name that deletion was attempted on.

        Raises:
            AttributeError: Always.
        """
        raise AttributeError(
            f"{type(self).__name__} is immutable: cannot delete {name!r}"
        )
