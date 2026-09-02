"""Bind: chaining box-producing functions together."""

from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from ekans.apply import Apply

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")


class Bind(Apply[A_co], Generic[A_co]):
    """An Apply that can chain box-producing functions together.

    Concrete types implement `bind`, overriding the parameter and
    return type with their own precise shape (e.g. `Identity[A]`
    implements `bind(self, f: Callable[[A], Identity[B]]) -> Identity[B]`).
    """

    @abstractmethod
    def bind(self, f: Callable[[A_co], "Bind[B]"]) -> "Bind[B]":
        """Apply `f` to the wrapped value(s), flattening the result.

        Unlike `fmap`, `f` itself returns a wrapped value -- `bind`
        doesn't leave a box of boxes behind, per the associativity
        law: `m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))`.

        Args:
            f: A function from the wrapped value to a new Bind of the
                same shape.

        Returns:
            The result of applying `f`, flattened into a single Bind
            of the same shape.
        """
        raise NotImplementedError


def bind(f: Callable[[A], "Bind[B]"], x: "Bind[A]") -> "Bind[B]":
    """Free-function form of `Bind.bind`; delegates to the method.

    As each new concrete Bind type is added, this gains its own
    `@overload` (above the loose `Bind[A]` fallback, which must stay
    last) so calls against a known concrete type keep a precise
    return type -- same pattern `ap` uses in `apply.py`.

    Args:
        f: A function from the wrapped value to a new Bind of the
            same shape.
        x: The wrapped value to apply it to.

    Returns:
        The result of `x.bind(f)`.
    """
    return x.bind(f)
