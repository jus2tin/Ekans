"""Foldable: anything iterable, plus the pure-fold slice of Data.Foldable."""

from abc import ABC, abstractmethod
from typing import (
    Callable,
    Generic,
    Iterator,
    Protocol,
    Type,
    TypeVar,
    runtime_checkable,
)

from ekans.monoid import Monoid
from ekans.semigroup import Semigroup

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")
M = TypeVar("M", bound=Monoid)
S = TypeVar("S", bound=Semigroup)


@runtime_checkable
class Foldable(Protocol[A_co]):
    """Anything iterable.

    Structural, not nominal -- any type with `__iter__` satisfies this
    automatically, no explicit inheritance needed. See CLAUDE.md's
    "Why Foldable is a Protocol" for the full reasoning.
    """

    def __iter__(self) -> Iterator[A_co]: ...


class FoldableABC(ABC, Generic[A_co]):
    """Optional base for a concrete type to override `foldr`/`length`
    with something faster than the generic `__iter__`-driven default.

    Free functions check for the override first (`isinstance(x,
    FoldableABC)` and catching the sentinel `NotImplementedError`),
    falling back to the generic default otherwise. `__iter__` is a
    real abstract requirement; `foldr`/`length` are not -- a subclass
    is never required to override them.
    """

    @abstractmethod
    def __iter__(self) -> Iterator[A_co]:
        raise NotImplementedError

    def foldr(self, f: Callable[[A_co, B], B], initial: B) -> B:
        """Override point for a faster right fold than the generic default.

        Args:
            f: Combines one element with the accumulated result so far.
            initial: The seed value.

        Returns:
            The folded result.

        Raises:
            NotImplementedError: Always, unless overridden -- the
                sentinel signaling "use the generic default."
        """
        raise NotImplementedError

    def length(self) -> int:
        """Override point for an O(1) length instead of counting via `__iter__`.

        Returns:
            The number of elements.

        Raises:
            NotImplementedError: Always, unless overridden -- the
                sentinel signaling "use the generic default."
        """
        raise NotImplementedError


def foldr(f: Callable[[A, B], B], initial: B, xs: Foldable[A]) -> B:
    """Right fold: `foldr f z [x1..xn] == f x1 (f x2 (... (f xn z)))`.

    Args:
        f: Combines one element with the accumulated result so far.
        initial: The seed value (used when `xs` is empty).
        xs: Anything iterable.

    Returns:
        The folded result. Uses `xs`'s own `FoldableABC.foldr`
        override if present; otherwise a stack-safe accumulator loop
        over `reversed(list(xs))` -- verified not to need real
        recursion, unlike a naive chain of thunks (see
        docs/specs/foldable.md's Design section).
    """
    if isinstance(xs, FoldableABC):
        try:
            return xs.foldr(f, initial)
        except NotImplementedError:
            pass
    acc = initial
    for item in reversed(list(xs)):
        acc = f(item, acc)
    return acc


def foldl(f: Callable[[B, A], B], initial: B, xs: Foldable[A]) -> B:
    """Left fold: `foldl f z [x1..xn] == f (... (f (f z x1) x2) ...) xn`.

    Args:
        f: Combines the accumulated result so far with one element.
        initial: The seed value.
        xs: Anything iterable.

    Returns:
        The folded result. Trivially stack-safe -- a plain forward
        accumulator loop, no reversal needed.
    """
    acc = initial
    for item in xs:
        acc = f(acc, item)
    return acc


def foldMap(monoid_type: Type[M], f: Callable[[A], M], xs: Foldable[A]) -> M:
    """Map each element into a Monoid and combine via `mappend`/`mempty`.

    Args:
        monoid_type: The concrete Monoid type `f` produces -- needed
            explicitly since an empty `xs` has no runtime value to
            call `.mempty()` on otherwise (same erasure reason as
            `Sum.mempty()`).
        f: Maps each element into `monoid_type`.
        xs: Anything iterable.

    Returns:
        `monoid_type.mempty()` combined with `f(x)` for every `x` in
        `xs`, in order.
    """
    result = monoid_type.mempty()
    for item in xs:
        result = result.mappend(f(item))
    return result


def fold(monoid_type: Type[M], xs: Foldable[M]) -> M:
    """`foldMap` with `f` as the identity -- the elements are already the Monoid.

    Args:
        monoid_type: The concrete Monoid type `xs`'s elements are.
        xs: Anything iterable of `monoid_type` values.

    Returns:
        Every element combined via `mappend`, starting from `mempty()`.
    """
    return foldMap(monoid_type, lambda x: x, xs)


def foldr1(f: Callable[[A, A], A], xs: Foldable[A]) -> A:
    """`foldr` with the last element as the seed instead of an explicit one.

    Args:
        f: Combines one element with the accumulated result so far.
        xs: Anything iterable.

    Returns:
        The folded result.

    Raises:
        ValueError: If `xs` is empty (matching Haskell's own
            partiality here).
    """
    items = list(xs)
    if not items:
        raise ValueError("foldr1: empty Foldable")
    *init, last = items
    acc = last
    for item in reversed(init):
        acc = f(item, acc)
    return acc


def foldl1(f: Callable[[A, A], A], xs: Foldable[A]) -> A:
    """`foldl` with the first element as the seed instead of an explicit one.

    Args:
        f: Combines the accumulated result so far with one element.
        xs: Anything iterable.

    Returns:
        The folded result.

    Raises:
        ValueError: If `xs` is empty.
    """
    items = list(xs)
    if not items:
        raise ValueError("foldl1: empty Foldable")
    acc = items[0]
    for item in items[1:]:
        acc = f(acc, item)
    return acc


def fold1(xs: Foldable[S]) -> S:
    """`Semigroup`-only, seedless fold -- no `Type[M]` needed since
    there's no empty case to conjure a value for.

    Args:
        xs: Anything iterable of Semigroup values.

    Returns:
        Every element combined via `mappend`.

    Raises:
        ValueError: If `xs` is empty.
    """
    items = list(xs)
    if not items:
        raise ValueError("fold1: empty Foldable")
    acc = items[0]
    for item in items[1:]:
        acc = acc.mappend(item)
    return acc
