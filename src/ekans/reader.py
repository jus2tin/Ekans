"""Reader: the function arrow `(-> r)` as a first-class value."""

from typing import Callable, TypeVar

A = TypeVar("A")
C = TypeVar("C")


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
