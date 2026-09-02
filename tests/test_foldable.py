import builtins
import sys
from dataclasses import dataclass
from functools import reduce
from typing import Callable, Iterator, List, TypeVar

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ekans.foldable import (
    Foldable,
    FoldableABC,
    all,
    and_,
    any,
    concat,
    concatMap,
    elem,
    find,
    fold,
    fold1,
    foldl,
    foldl1,
    foldMap,
    foldr,
    foldr1,
    length,
    maximum,
    maximumBy,
    minimum,
    minimumBy,
    notElem,
    null,
    or_,
    product,
    sum,
    toList,
)
from ekans.maybe import Just, Nothing
from ekans.monoid import Monoid
from ekans.semigroup import Semigroup

A = TypeVar("A")


@dataclass(frozen=True)
class _MyIterable:
    items: List[int]

    def __iter__(self) -> Iterator[int]:
        return iter(self.items)


@dataclass(frozen=True, eq=False)
class _SemiBox(Semigroup):
    value: int

    def mappend(self, other: "_SemiBox") -> "_SemiBox":
        return _SemiBox(value=self.value + other.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _SemiBox) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _MonoidBox(Monoid):
    value: int

    def mappend(self, other: "_MonoidBox") -> "_MonoidBox":
        return _MonoidBox(value=self.value + other.value)

    @classmethod
    def mempty(cls) -> "_MonoidBox":
        return _MonoidBox(value=0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _MonoidBox) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


def test_list_satisfies_foldable() -> None:
    assert isinstance([1, 2, 3], Foldable)


def test_tuple_satisfies_foldable() -> None:
    assert isinstance((1, 2, 3), Foldable)


def test_generator_satisfies_foldable() -> None:
    assert isinstance((x for x in range(3)), Foldable)


def test_custom_iterable_satisfies_foldable_without_inheritance() -> None:
    assert isinstance(_MyIterable(items=[1, 2, 3]), Foldable)


def test_non_iterable_does_not_satisfy_foldable() -> None:
    assert not isinstance(5, Foldable)


def test_foldable_abc_requires_iter() -> None:
    with pytest.raises(TypeError):
        FoldableABC()  # type: ignore[abstract]


def test_foldable_abc_iter_raises_if_not_overridden() -> None:
    @dataclass(frozen=True)
    class _Bare(FoldableABC[int]):
        def __iter__(self) -> Iterator[int]:
            return iter(())

    with pytest.raises(NotImplementedError):
        FoldableABC.__iter__(_Bare())


def test_foldable_abc_length_raises_if_not_overridden() -> None:
    @dataclass(frozen=True)
    class _Bare(FoldableABC[int]):
        def __iter__(self) -> Iterator[int]:
            return iter(())

    with pytest.raises(NotImplementedError):
        _Bare().length()


def test_foldr_basic() -> None:
    assert foldr(lambda a, b: a + b, 0, [1, 2, 3, 4, 5]) == 15


def test_foldr_preserves_right_associativity() -> None:
    # foldr (-) 0 [1,2,3] == 1 - (2 - (3 - 0)) == 2
    assert foldr(lambda a, b: a - b, 0, [1, 2, 3]) == 2


@given(st.lists(st.integers(), max_size=50))
def test_foldr_matches_python_sum(xs: List[int]) -> None:
    assert foldr(lambda a, b: a + b, 0, xs) == builtins.sum(xs)


def test_foldr_is_stack_safe_for_a_large_input() -> None:
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(200)
    try:
        big = list(range(100_000))
        result = foldr(lambda a, b: a + b, 0, big)
    finally:
        sys.setrecursionlimit(old_limit)
    assert result == builtins.sum(big)


def test_foldl_basic() -> None:
    assert foldl(lambda a, b: a + b, 0, [1, 2, 3, 4, 5]) == 15


def test_foldl_preserves_left_associativity() -> None:
    # foldl (-) 0 [1,2,3] == ((0 - 1) - 2) - 3 == -6
    assert foldl(lambda a, b: a - b, 0, [1, 2, 3]) == -6


@given(st.lists(st.integers(), max_size=50), st.integers())
def test_foldl_matches_python_reduce(xs: List[int], initial: int) -> None:
    assert foldl(lambda a, b: a - b, initial, xs) == reduce(
        lambda a, b: a - b, xs, initial
    )


def test_foldl_is_stack_safe_for_a_large_input() -> None:
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(200)
    try:
        big = list(range(100_000))
        result = foldl(lambda a, b: a + b, 0, big)
    finally:
        sys.setrecursionlimit(old_limit)
    assert result == builtins.sum(big)


def test_foldable_abc_foldr_override_is_used() -> None:
    calls: List[str] = []

    @dataclass(frozen=True)
    class _Logged(FoldableABC[int]):
        items: List[int]

        def __iter__(self) -> Iterator[int]:
            calls.append("iter")
            return iter(self.items)

        def foldr(self, f: Callable[[int, A], A], initial: A) -> A:
            calls.append("foldr-override")
            result = initial
            for item in reversed(self.items):
                result = f(item, result)
            return result

    logged = _Logged(items=[1, 2, 3])
    assert foldr(lambda a, b: a + b, 0, logged) == 6
    assert "foldr-override" in calls
    assert "iter" not in calls  # the override never needed to iterate itself


def test_foldr_falls_back_to_generic_default_without_an_override() -> None:
    @dataclass(frozen=True)
    class _PlainFoldableABC(FoldableABC[int]):
        items: List[int]

        def __iter__(self) -> Iterator[int]:
            return iter(self.items)

    plain = _PlainFoldableABC(items=[1, 2, 3])
    assert foldr(lambda a, b: a + b, 0, plain) == 6


def test_foldMap_combines_via_mappend() -> None:
    result = foldMap(_MonoidBox, lambda a: _MonoidBox(value=a), [1, 2, 3])
    assert result == _MonoidBox(value=6)


def test_foldMap_on_empty_returns_mempty() -> None:
    result = foldMap(_MonoidBox, lambda a: _MonoidBox(value=a), [])
    assert result == _MonoidBox(value=0)


def test_fold_combines_already_wrapped_values() -> None:
    result = fold(_MonoidBox, [_MonoidBox(value=1), _MonoidBox(value=2)])
    assert result == _MonoidBox(value=3)


def test_fold_on_empty_returns_mempty() -> None:
    assert fold(_MonoidBox, []) == _MonoidBox(value=0)


def test_foldr1_basic() -> None:
    assert foldr1(lambda a, b: a - b, [1, 2, 3]) == 2  # 1 - (2 - 3)


def test_foldr1_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        foldr1(lambda a, b: a - b, [])


def test_foldl1_basic() -> None:
    assert foldl1(lambda a, b: a - b, [1, 2, 3]) == -4  # (1 - 2) - 3


def test_foldl1_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        foldl1(lambda a, b: a - b, [])


def test_fold1_combines_semigroup_values() -> None:
    result = fold1([_SemiBox(value=1), _SemiBox(value=2), _SemiBox(value=3)])
    assert result == _SemiBox(value=6)


def test_fold1_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        fold1([])


def test_toList_basic() -> None:
    assert toList((1, 2, 3)) == [1, 2, 3]


def test_toList_from_generator() -> None:
    assert toList(x for x in range(3)) == [0, 1, 2]


def test_null_true_for_empty() -> None:
    assert null([]) is True


def test_null_false_for_nonempty() -> None:
    assert null([1]) is False


def test_length_basic() -> None:
    assert length([1, 2, 3, 4]) == 4


@given(st.lists(st.integers(), max_size=50))
def test_length_matches_python_len(xs: List[int]) -> None:
    assert length(xs) == len(xs)


def test_length_uses_foldable_abc_override() -> None:
    calls: List[str] = []

    @dataclass(frozen=True)
    class _Counted(FoldableABC[int]):
        items: List[int]

        def __iter__(self) -> Iterator[int]:
            calls.append("iter")
            return iter(self.items)

        def length(self) -> int:
            calls.append("length-override")
            return len(self.items)

    counted = _Counted(items=[1, 2, 3])
    assert length(counted) == 3
    assert "length-override" in calls
    assert "iter" not in calls


def test_length_falls_back_to_generic_default_without_an_override() -> None:
    @dataclass(frozen=True)
    class _PlainFoldableABC(FoldableABC[int]):
        items: List[int]

        def __iter__(self) -> Iterator[int]:
            return iter(self.items)

    assert length(_PlainFoldableABC(items=[1, 2, 3])) == 3


def test_concat_flattens_a_foldable_of_iterables() -> None:
    assert concat([[1, 2], [3], [4, 5]]) == [1, 2, 3, 4, 5]


def test_concatMap_maps_then_flattens() -> None:
    assert concatMap(lambda a: [a, a], [1, 2, 3]) == [1, 1, 2, 2, 3, 3]


def test_and__true_when_all_true() -> None:
    assert and_([True, True, True]) is True


def test_and__false_when_one_false() -> None:
    assert and_([True, False, True]) is False


def test_or__true_when_any_true() -> None:
    assert or_([False, True, False]) is True


def test_or__false_when_all_false() -> None:
    assert or_([False, False, False]) is False


def test_any_true() -> None:
    assert any(lambda a: a > 3, [1, 2, 3, 4]) is True


def test_any_false() -> None:
    assert any(lambda a: a > 10, [1, 2, 3, 4]) is False


def test_any_short_circuits() -> None:
    calls: List[int] = []

    def predicate(a: int) -> bool:
        calls.append(a)
        return a > 1

    assert any(predicate, [1, 2, 3, 4]) is True
    assert calls == [1, 2]


def test_all_true() -> None:
    assert all(lambda a: a > 0, [1, 2, 3, 4]) is True


def test_all_false() -> None:
    assert all(lambda a: a > 2, [1, 2, 3, 4]) is False


def test_all_short_circuits() -> None:
    calls: List[int] = []

    def predicate(a: int) -> bool:
        calls.append(a)
        return a < 2

    assert all(predicate, [1, 2, 3, 4]) is False
    assert calls == [1, 2]


def test_elem_true() -> None:
    assert elem(3, [1, 2, 3, 4]) is True


def test_elem_false() -> None:
    assert elem(10, [1, 2, 3, 4]) is False


def test_notElem_true() -> None:
    assert notElem(10, [1, 2, 3, 4]) is True


def test_notElem_false() -> None:
    assert notElem(3, [1, 2, 3, 4]) is False


def test_find_returns_first_match_wrapped_in_just() -> None:
    assert find(lambda a: a > 2, [1, 2, 3, 4]) == Just(value=3)


def test_find_returns_nothing_when_no_match() -> None:
    result = find(lambda a: a > 100, [1, 2, 3, 4])
    assert result == Nothing()


def test_find_short_circuits() -> None:
    calls: List[int] = []

    def predicate(a: int) -> bool:
        calls.append(a)
        return a == 2

    find(predicate, [1, 2, 3, 4])
    assert calls == [1, 2]


def test_sum_basic() -> None:
    assert sum([1, 2, 3, 4], 0) == 10


def test_sum_empty_returns_start() -> None:
    assert sum([], 100) == 100


@given(st.lists(st.integers(), max_size=50), st.integers())
def test_sum_matches_python_sum(xs: List[int], start: int) -> None:
    assert sum(xs, start) == builtins.sum(xs, start)


def test_product_basic() -> None:
    assert product([1, 2, 3, 4], 1) == 24


def test_product_empty_returns_start() -> None:
    assert product([], 7) == 7


def test_maximum_basic() -> None:
    assert maximum([3, 1, 4, 1, 5, 9, 2, 6]) == 9


@given(st.lists(st.integers(), min_size=1, max_size=50))
def test_maximum_matches_python_max(xs: List[int]) -> None:
    assert maximum(xs) == builtins.max(xs)


def test_maximum_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        maximum([])


def test_minimum_basic() -> None:
    assert minimum([3, 1, 4, 1, 5, 9, 2, 6]) == 1


@given(st.lists(st.integers(), min_size=1, max_size=50))
def test_minimum_matches_python_min(xs: List[int]) -> None:
    assert minimum(xs) == builtins.min(xs)


def test_minimum_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        minimum([])


def test_maximumBy_basic() -> None:
    words = ["a", "abc", "ab"]
    assert maximumBy(len, words) == "abc"


def test_maximumBy_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        maximumBy(len, [])


def test_minimumBy_basic() -> None:
    words = ["abc", "a", "ab"]
    assert minimumBy(len, words) == "a"


def test_minimumBy_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        minimumBy(len, [])
