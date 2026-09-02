"""Reader: the function arrow `(-> r)` as a first-class value."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Type, TypeVar

from ekans.applicative import Applicative

if TYPE_CHECKING:
    from ekans.monoid import Monoid

A = TypeVar("A")
C = TypeVar("C")
R = TypeVar("R")
B = TypeVar("B")
S = TypeVar("S", bound="Monoid")


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
class Reader(Applicative[A], Generic[R, A]):
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

    # mypy flags both the parameter and return type here as
    # incompatible with Pointed.point's supertype signature
    # ([override]): point's types are method-scoped TypeVars, not a
    # self-bound one, so mypy can't establish the substitutability it
    # can for instance methods like fmap -- narrowing here is the point.
    @classmethod
    def point(cls, value: A) -> "Reader[R, A]":  # type: ignore[override]
        """Construct a Reader that ignores its environment and returns `value`.

        Args:
            value: The value the constructed Reader should always produce.

        Returns:
            A new Reader whose `run` ignores its argument and returns `value`.
        """
        return Reader(run=const(value))

    def ap(  # type: ignore[override]
        self, f: "Reader[R, Callable[[A], B]]"
    ) -> "Reader[R, B]":
        """Apply the function wrapped in `f`, threading the same environment.

        Args:
            f: A Reader wrapping the function to apply.

        Returns:
            A new Reader whose `run` calls both `self.run` and `f.run`
            with the same environment, then applies one result to the
            other.
        """
        return Reader(run=lambda r: f.run(r)(self.run(r)))

    def __call__(self, r: R) -> A:
        """Delegate to `run`, so a Reader can be used like a plain function.

        Args:
            r: The environment to run against.

        Returns:
            The result of `self.run(r)`.
        """
        return self.run(r)

    @classmethod
    def mempty(cls, value_type: Type[S]) -> "Reader[R, S]":
        """Construct the identity element for `value_type`, pointwise.

        Does not override `Monoid.mempty` -- same non-nominal
        reasoning as `Identity.mempty`/`Const.mempty`. Ignores the
        environment entirely, same shape as `Reader.point`/`const`.
        `R` is freely inferred from context, unrelated to `S`.

        Args:
            value_type: The concrete Monoid type to build the identity
                for.

        Returns:
            A new Reader whose `run` ignores its argument and returns
            `value_type.mempty()`.
        """
        return Reader(run=const(value_type.mempty()))
