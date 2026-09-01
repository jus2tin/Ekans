"""Reader: the function arrow `(-> r)` as a first-class value."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.functor import Functor

A = TypeVar("A")
C = TypeVar("C")
R = TypeVar("R")
B = TypeVar("B")


def const(value: A) -> Callable[[C], A]:
    """Build a function that ignores its argument and always returns `value`.

    Haskell's `const :: a -> b -> a`, spelled as a function returning a
    function since this project doesn't curry by default (see
    CLAUDE.md's Currying section) -- `Reader.point` needs a
    `Callable[[R], A]` directly.

    Args:
        value: The value the returned function should always produce.

    Returns:
        A function that ignores whatever it's given and returns `value`.
    """

    def _ignore(_: C) -> A:
        return value

    return _ignore


@dataclass(frozen=True, eq=False)
class Reader(Functor[A], Generic[R, A]):
    """The function arrow `(-> r)`: wraps a function from an environment to a result.

    Deliberately has no `__eq__`/`__hash__` override, unlike Identity/
    Const -- functions aren't structurally comparable in Python, so a
    reference-based default is the honest choice. See
    docs/specs/reader.md's Equality section.

    Attributes:
        run: The wrapped function, from environment to result.
    """

    run: Callable[[R], A]

    def fmap(self, f: Callable[[A], B]) -> "Reader[R, B]":
        """Compose `f` onto the wrapped function's result.

        Args:
            f: The function to apply to the wrapped function's result.

        Returns:
            A new Reader whose wrapped function is `f` composed after `run`.
        """
        return Reader(run=lambda r: f(self.run(r)))
