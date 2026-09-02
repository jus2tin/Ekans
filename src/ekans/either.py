"""Either: L or R, biased to R."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, Iterator, TypeVar, Union

from ekans.monad import Monad

L = TypeVar("L")
R = TypeVar("R")
R2 = TypeVar("R2")


class Either(Monad[R], Generic[L, R]):
    """`L` or `R`: `Left(value)` or `Right(value)`, biased to `Right`.

    `fmap`/`ap`/`bind` are re-declared here (not just inherited from
    `Monad`) specifically to narrow their return type to
    `Union[Left[L, R2], Right[L, R2]]` instead of the abstract
    `Either[L, R2]` -- same `match`/`case` exhaustiveness reasoning
    `Maybe` established, verified fresh for `Either` (see
    docs/specs/either.md's Design section).
    """

    @abstractmethod
    def fmap(self, f: Callable[[R], R2]) -> "Union[Left[L, R2], Right[L, R2]]":
        """Apply `f` to the `Right` value, if this is a `Right`.

        Args:
            f: The function to apply to the `Right` value.

        Returns:
            `Right(f(value))` if this is a `Right`; `Left` unchanged
            (re-tagged) otherwise.
        """
        raise NotImplementedError

    # mypy flags both the parameter and return type here as
    # incompatible with Pointed.point's supertype signature
    # ([override]): point's types are method-scoped TypeVars, not a
    # self-bound one, so mypy can't establish the substitutability it
    # can for instance methods like fmap -- narrowing here is the point.
    @classmethod
    def point(  # type: ignore[override]
        cls, value: R
    ) -> "Union[Left[L, R], Right[L, R]]":
        """Construct a `Right` wrapping `value`.

        Matches Haskell's `pure = Right`. The one method in this
        hierarchy with a single correct implementation regardless of
        variant -- defined once here, not re-implemented on
        `Left`/`Right`.

        Args:
            value: The value to wrap.

        Returns:
            `Right(value=value)`.
        """
        return Right(value=value)

    @abstractmethod
    def ap(  # type: ignore[override]
        self, f: "Either[L, Callable[[R], R2]]"
    ) -> "Union[Left[L, R2], Right[L, R2]]":
        """Apply the function wrapped in `f`, if both sides are `Right`.

        Args:
            f: An Either wrapping the function to apply.

        Returns:
            `Right(f.value(value))` if both `self` and `f` are
            `Right`; the first `Left` encountered otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def bind(  # type: ignore[override]
        self, f: Callable[[R], "Either[L, R2]"]
    ) -> "Union[Left[L, R2], Right[L, R2]]":
        """Apply `f` to the `Right` value and flatten, if this is a `Right`.

        Args:
            f: A function from the `Right` value to a new Either.

        Returns:
            `f(value)` if this is a `Right`; `Left` unchanged
            (re-tagged, `f` never called) otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def __iter__(self) -> Iterator[R]:
        """Yield the `Right` value, if this is a `Right`.

        Returns:
            An iterator yielding `self.value` for a `Right`, nothing
            for a `Left`.
        """
        raise NotImplementedError


@dataclass(frozen=True, eq=False)
class Left(Either[L, R], Generic[L, R]):
    """Holds a value of type `L`; `R` is untouched.

    Attributes:
        value: The wrapped value.
    """

    value: L

    def fmap(self, f: Callable[[R], R2]) -> "Left[L, R2]":
        """Return `Left` unchanged; there's no `R` value to apply `f` to.

        Args:
            f: Ignored.

        Returns:
            A new Left holding the same value, re-tagged to Left[L, R2].
        """
        return Left(value=self.value)

    def ap(  # type: ignore[override]
        self, f: "Either[L, Callable[[R], R2]]"
    ) -> "Left[L, R2]":
        """Return `Left` unchanged; there's no `R` value to apply anything to.

        Args:
            f: Ignored.

        Returns:
            A new Left holding the same value, re-tagged to Left[L, R2].
        """
        return Left(value=self.value)

    def bind(  # type: ignore[override]
        self, f: Callable[[R], "Either[L, R2]"]
    ) -> "Left[L, R2]":
        """Return `Left` unchanged; `f` is never called.

        Args:
            f: Ignored.

        Returns:
            A new Left holding the same value, re-tagged to Left[L, R2].
        """
        return Left(value=self.value)

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Either[L, R]") -> bool:  # type: ignore[override]
        """Compare against another Either wrapping the same types.

        Typed against ``Either[L, R]`` so that mypy rejects
        comparisons between differently-parameterized Either
        instances (on either type parameter) at type-check time.

        Args:
            other: Another Either wrapping the same L and R.

        Returns:
            Whether `other` is a `Left` wrapping an equal value, or
            ``NotImplemented`` if `other` isn't an Either at all.
        """
        if not isinstance(other, Either):
            return NotImplemented
        return isinstance(other, Left) and bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)

    def __iter__(self) -> Iterator[R]:
        """Yield nothing -- `Left` has no `R` value.

        Returns:
            An empty iterator.
        """
        return iter(())


@dataclass(frozen=True, eq=False)
class Right(Either[L, R], Generic[L, R]):
    """Holds a value of type `R`; `L` is untouched.

    Attributes:
        value: The wrapped value.
    """

    value: R

    def fmap(self, f: Callable[[R], R2]) -> "Right[L, R2]":
        """Apply `f` to the wrapped value.

        Args:
            f: The function to apply.

        Returns:
            A new Right wrapping the result of `f(self.value)`.
        """
        return Right(value=f(self.value))

    def ap(  # type: ignore[override]
        self, f: "Either[L, Callable[[R], R2]]"
    ) -> "Union[Left[L, R2], Right[L, R2]]":
        """Apply the function wrapped in `f`, if `f` is a `Right`.

        Args:
            f: An Either wrapping the function to apply.

        Returns:
            `Right(f.value(self.value))` if `f` is a `Right`; `f`
            unchanged if `f` is `Left`.
        """
        match f:
            case Right(value=fn):
                return Right(value=fn(self.value))
            case Left(value=lv):
                return Left(value=lv)
            case _:
                # `f`'s static type is the abstract Either[L,
                # Callable[...]] -- mypy can't prove a match over an
                # ABC handle is exhaustive (see
                # docs/specs/either.md's Design section), so this
                # stays unreachable at runtime but satisfies the type
                # checker's missing-return check.
                raise AssertionError("unreachable")

    def bind(  # type: ignore[override]
        self, f: Callable[[R], "Either[L, R2]"]
    ) -> "Union[Left[L, R2], Right[L, R2]]":
        """Apply `f` to the wrapped value, flattening the result.

        Args:
            f: A function from the wrapped value to a new Either.

        Returns:
            The result of `f(self.value)`.
        """
        result = f(self.value)
        match result:
            case Left():
                return result
            case Right():
                return result
            case _:
                # Same reasoning as `ap` above -- `f`'s declared
                # return type is the abstract Either[L, R2], not
                # provably narrowed to Left[L, R2] | Right[L, R2]
                # without this match.
                raise AssertionError("unreachable")

    def __eq__(self, other: "Either[L, R]") -> bool:  # type: ignore[override]
        """Compare against another Either wrapping the same types.

        Args:
            other: Another Either wrapping the same L and R.

        Returns:
            Whether `other` is a `Right` wrapping an equal value, or
            ``NotImplemented`` if `other` isn't an Either at all.
        """
        if not isinstance(other, Either):
            return NotImplemented
        return isinstance(other, Right) and bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped value.

        Returns:
            The hash of the wrapped value.
        """
        return hash(self.value)

    def __iter__(self) -> Iterator[R]:
        """Yield the wrapped value.

        Returns:
            An iterator yielding exactly `self.value`.
        """
        yield self.value
