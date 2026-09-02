"""Foldable: anything iterable, plus the pure-fold slice of Data.Foldable."""

from abc import ABC, abstractmethod
from typing import (
    Callable,
    Generic,
    Iterable,
    Iterator,
    List,
    Protocol,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

from ekans.maybe import Just, Nothing
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


def toList(xs: Foldable[A]) -> List[A]:
    """Materialize `xs` into a plain list.

    Args:
        xs: Anything iterable.

    Returns:
        Every element of `xs`, in order, as a `list`.
    """
    return list(xs)


def null(xs: Foldable[A]) -> bool:
    """Whether `xs` has no elements.

    Args:
        xs: Anything iterable.

    Returns:
        `True` if `xs` is empty.
    """
    for _ in xs:
        return False
    return True


def length(xs: Foldable[A]) -> int:
    """The number of elements in `xs`.

    Args:
        xs: Anything iterable.

    Returns:
        The element count. Uses `xs`'s own `FoldableABC.length`
        override if present; otherwise counts via `__iter__`.
    """
    if isinstance(xs, FoldableABC):
        try:
            return xs.length()
        except NotImplementedError:
            pass
    count = 0
    for _ in xs:
        count += 1
    return count


def concat(xs: "Foldable[Iterable[A]]") -> List[A]:
    """Flatten a Foldable of iterables into one list.

    Args:
        xs: Anything iterable of iterables.

    Returns:
        Every element of every inner iterable, in order.
    """
    result: List[A] = []
    for inner in xs:
        result.extend(inner)
    return result


def concatMap(f: Callable[[A], Iterable[B]], xs: Foldable[A]) -> List[B]:
    """Map each element to an iterable, then flatten the results.

    Args:
        f: Maps each element to an iterable.
        xs: Anything iterable.

    Returns:
        Every element of every `f(x)`, in order.
    """
    result: List[B] = []
    for item in xs:
        result.extend(f(item))
    return result


def and_(xs: Foldable[bool]) -> bool:
    """Whether every element is `True`.

    Named with a trailing underscore since `and` is a Python keyword
    and can't be used as a function name at all -- matching the
    stdlib `operator` module's own convention for the same problem
    (`operator.and_`).

    Args:
        xs: Anything iterable of `bool`.

    Returns:
        `True` if every element is `True` (vacuously `True` if `xs`
        is empty).
    """
    for item in xs:
        if not item:
            return False
    return True


def or_(xs: Foldable[bool]) -> bool:
    """Whether any element is `True`.

    Args:
        xs: Anything iterable of `bool`.

    Returns:
        `True` if at least one element is `True` (`False` if `xs` is
        empty).
    """
    for item in xs:
        if item:
            return True
    return False


def any(predicate: Callable[[A], bool], xs: Foldable[A]) -> bool:
    """Whether `predicate` holds for at least one element.

    Short-circuits: stops at the first match, never scans the rest.

    Args:
        predicate: The condition to test each element against.
        xs: Anything iterable.

    Returns:
        `True` if `predicate` holds for at least one element.
    """
    for item in xs:
        if predicate(item):
            return True
    return False


def all(predicate: Callable[[A], bool], xs: Foldable[A]) -> bool:
    """Whether `predicate` holds for every element.

    Short-circuits: stops at the first failure, never scans the rest.

    Args:
        predicate: The condition to test each element against.
        xs: Anything iterable.

    Returns:
        `True` if `predicate` holds for every element.
    """
    for item in xs:
        if not predicate(item):
            return False
    return True


def elem(x: A, xs: Foldable[A]) -> bool:
    """Whether `x` is in `xs`, via `==`. Short-circuits.

    Args:
        x: The value to look for.
        xs: Anything iterable.

    Returns:
        `True` if any element of `xs` equals `x`.
    """
    for item in xs:
        if item == x:
            return True
    return False


def notElem(x: A, xs: Foldable[A]) -> bool:
    """The negation of `elem`. Short-circuits.

    Args:
        x: The value to look for.
        xs: Anything iterable.

    Returns:
        `True` if no element of `xs` equals `x`.
    """
    return not elem(x, xs)


def find(
    predicate: Callable[[A], bool], xs: Foldable[A]
) -> "Union[Just[A], Nothing[A]]":
    """The first element satisfying `predicate`, wrapped in `Maybe`.

    Matches Haskell's own `find :: (a -> Bool) -> t a -> Maybe a`
    signature directly. Short-circuits: stops at the first match.

    Args:
        predicate: The condition to test each element against.
        xs: Anything iterable.

    Returns:
        `Just` the first matching element, or `Nothing` if none match.
    """
    for item in xs:
        if predicate(item):
            return Just(value=item)
    return Nothing()
