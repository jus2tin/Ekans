"""Maybe: a value that might not be there."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union

from ekans.monad import Monad

A = TypeVar("A")
B = TypeVar("B")


class Maybe(Monad[A], Generic[A]):
    """A value that might not be there: `Just(value)` or `Nothing`.

    `fmap`/`ap`/`bind` are re-declared here (not just inherited from
    `Monad`) specifically to narrow their return type to
    `Union[Just[B], Nothing[B]]` instead of the abstract `Maybe[B]` --
    required for real `match`/`case` exhaustiveness and field
    narrowing under `mypy --strict` (verified in Phase 1: the
    `Maybe[B]`-returning version produces a genuine `Missing return
    statement` error on an exhaustive two-case `match`, and
    `Any`-typed narrowing inside `case Just(value=v):`).
    """

    @abstractmethod
    def fmap(self, f: Callable[[A], B]) -> "Union[Just[B], Nothing[B]]":
        """Apply `f` to the wrapped value, if there is one.

        Args:
            f: The function to apply to the wrapped value.

        Returns:
            `Just(f(value))` if this is a `Just`; `Nothing` otherwise.
        """
        raise NotImplementedError

    # mypy flags both the parameter and return type here as
    # incompatible with Pointed.point's supertype signature
    # ([override]): point's types are method-scoped TypeVars, not a
    # self-bound one, so mypy can't establish the substitutability it
    # can for instance methods like fmap -- narrowing here is the point.
    @classmethod
    def point(cls, value: A) -> "Union[Just[A], Nothing[A]]":  # type: ignore[override]
        """Construct a `Just` wrapping `value`.

        The one method in this hierarchy with a single correct
        implementation regardless of variant -- defined once here,
        not re-implemented on `Just`/`Nothing`.

        Args:
            value: The value to wrap.

        Returns:
            `Just(value=value)`.
        """
        return Just(value=value)

    @abstractmethod
    def ap(  # type: ignore[override]
        self, f: "Maybe[Callable[[A], B]]"
    ) -> "Union[Just[B], Nothing[B]]":
        """Apply the function wrapped in `f`, if both sides are present.

        Args:
            f: A Maybe wrapping the function to apply.

        Returns:
            `Just(f.value(value))` if both `self` and `f` are `Just`;
            `Nothing` otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def bind(  # type: ignore[override]
        self, f: Callable[[A], "Maybe[B]"]
    ) -> "Union[Just[B], Nothing[B]]":
        """Apply `f` to the wrapped value and flatten, if there is one.

        Args:
            f: A function from the wrapped value to a new Maybe.

        Returns:
            `f(value)` if this is a `Just`; `Nothing` otherwise (`f`
            is never called).
        """
        raise NotImplementedError


@dataclass(frozen=True, eq=False)
class Just(Maybe[A], Generic[A]):
    """Holds a real value of type `A`.

    Attributes:
        value: The wrapped value.
    """

    value: A

    def fmap(self, f: Callable[[A], B]) -> "Just[B]":
        """Apply `f` to the wrapped value.

        Args:
            f: The function to apply.

        Returns:
            A new Just wrapping the result of `f(self.value)`.
        """
        return Just(value=f(self.value))

    def ap(  # type: ignore[override]
        self, f: "Maybe[Callable[[A], B]]"
    ) -> "Union[Just[B], Nothing[B]]":
        """Apply the function wrapped in `f`, if `f` is a `Just`.

        Args:
            f: A Maybe wrapping the function to apply.

        Returns:
            `Just(f.value(self.value))` if `f` is a `Just`; `Nothing`
            if `f` is `Nothing`.
        """
        match f:
            case Just(value=fn):
                return Just(value=fn(self.value))
            case Nothing():
                return Nothing()
            case _:
                # `f`'s static type is the abstract Maybe[Callable[...]]
                # -- mypy can't prove a match over an ABC handle is
                # exhaustive (see docs/specs/maybe.md's Design section),
                # so this stays unreachable at runtime but satisfies the
                # type checker's missing-return check.
                raise AssertionError("unreachable")

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "Maybe[B]"]
    ) -> "Union[Just[B], Nothing[B]]":
        """Apply `f` to the wrapped value, flattening the result.

        Args:
            f: A function from the wrapped value to a new Maybe.

        Returns:
            The result of `f(self.value)`.
        """
        result = f(self.value)
        match result:
            case Just():
                return result
            case Nothing():
                return result
            case _:
                # Same reasoning as `ap` above -- `f`'s declared return
                # type is the abstract Maybe[B], not provably narrowed
                # to Just[B] | Nothing[B] without this match.
                raise AssertionError("unreachable")

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Maybe[A]") -> bool:  # type: ignore[override]
        """Compare against another Maybe wrapping the same type.

        Args:
            other: Another Maybe wrapping the same type of value.

        Returns:
            Whether `other` is a `Just` wrapping an equal value, or
            ``NotImplemented`` if `other` isn't a Maybe at all.
        """
        if not isinstance(other, Maybe):
            return NotImplemented
        return isinstance(other, Just) and bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class Nothing(Maybe[A], Generic[A]):
    """Holds nothing. Ekans' first genuinely zero-field concrete type."""

    def fmap(self, f: Callable[[A], B]) -> "Nothing[B]":
        """Return `Nothing`; there's no wrapped value to apply `f` to.

        Args:
            f: Ignored.

        Returns:
            A new Nothing, re-tagged to Nothing[B].
        """
        return Nothing()

    def ap(  # type: ignore[override]
        self, f: "Maybe[Callable[[A], B]]"
    ) -> "Nothing[B]":
        """Return `Nothing`; there's no wrapped value to apply anything to.

        Args:
            f: Ignored.

        Returns:
            A new Nothing, re-tagged to Nothing[B].
        """
        return Nothing()

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "Maybe[B]"]
    ) -> "Nothing[B]":
        """Return `Nothing`; `f` is never called.

        Args:
            f: Ignored.

        Returns:
            A new Nothing, re-tagged to Nothing[B].
        """
        return Nothing()

    def __eq__(self, other: "Maybe[A]") -> bool:  # type: ignore[override]
        """Compare against another Maybe wrapping the same type.

        Args:
            other: Another Maybe wrapping the same type of value.

        Returns:
            Whether `other` is also a `Nothing`, or ``NotImplemented``
            if `other` isn't a Maybe at all.
        """
        if not isinstance(other, Maybe):
            return NotImplemented
        return isinstance(other, Nothing)

    def __hash__(self) -> int:
        """Hash consistently with equality.

        Returns:
            A constant hash shared by every Nothing instance.
        """
        return 0
