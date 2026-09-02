from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar, Union

import pytest
from applicative_laws import assert_applicative_law
from apply_laws import assert_apply_law
from bind_laws import assert_bind_law
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st
from monad_laws import assert_monad_law

from ekans.applicative import Applicative
from ekans.apply import ap
from ekans.bind import Bind, bind
from ekans.either import Either, Left, Right
from ekans.functor import fmap
from ekans.monad import Monad

_L = TypeVar("_L")
_R = TypeVar("_R")
_R2 = TypeVar("_R2")


@dataclass(frozen=True, eq=False)
class _RogueEither(Either[_L, _R], Generic[_L, _R]):
    """A third Either variant, existing only to prove the `ap`/`bind`
    `case _: raise AssertionError` fallback (docs/specs/either.md's
    Design section) is a real safety net, not dead code.
    """

    def fmap(self, f: Callable[[_R], _R2]) -> "Right[_L, _R2]":
        raise NotImplementedError

    def ap(  # type: ignore[override]
        self, f: "Either[_L, Callable[[_R], _R2]]"
    ) -> "Union[Left[_L, _R2], Right[_L, _R2]]":
        raise NotImplementedError

    def bind(  # type: ignore[override]
        self, f: Callable[[_R], "Either[_L, _R2]"]
    ) -> "Union[Left[_L, _R2], Right[_L, _R2]]":
        raise NotImplementedError

    def __eq__(self, other: "Either[_L, _R]") -> bool:  # type: ignore[override]
        return isinstance(other, _RogueEither)

    def __hash__(self) -> int:
        return 0


def test_left_holds_the_value() -> None:
    assert Left(value=1).value == 1


def test_right_holds_the_value() -> None:
    assert Right(value=1).value == 1


def test_left_equal_when_values_are_equal() -> None:
    assert Left(value=1) == Left(value=1)


def test_left_not_equal_when_values_differ() -> None:
    assert Left(value=1) != Left(value=2)


def test_right_equal_when_values_are_equal() -> None:
    assert Right(value=1) == Right(value=1)


def test_right_not_equal_when_values_differ() -> None:
    assert Right(value=1) != Right(value=2)


def test_left_not_equal_to_right_even_with_equal_held_values() -> None:
    left: Either[int, int] = Left(value=1)
    right: Either[int, int] = Right(value=1)
    assert left != right
    assert right != left


def test_not_equal_to_an_unrelated_type() -> None:
    assert Left(value=1) != "not an Either"
    assert Right(value=1) != "not an Either"


def test_left_equal_values_hash_the_same() -> None:
    assert hash(Left(value=1)) == hash(Left(value=1))


def test_right_equal_values_hash_the_same() -> None:
    assert hash(Right(value=1)) == hash(Right(value=1))


def test_is_usable_as_a_set_member() -> None:
    assert {Right(value=1), Right(value=1), Right(value=2)} == {
        Right(value=1),
        Right(value=2),
    }


def test_left_is_immutable() -> None:
    left: Left[int, int] = Left(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        left.value = 2  # type: ignore[misc]


def test_right_is_immutable() -> None:
    right: Right[int, int] = Right(value=1)
    with pytest.raises(AttributeError):
        right.value = 2  # type: ignore[misc]


def test_right_fmap_applies_the_function_to_the_wrapped_value() -> None:
    assert Right(value=1).fmap(str) == Right(value="1")


def test_free_fmap_delegates_to_the_method_for_right() -> None:
    assert fmap(str, Right(value=1)) == Right(value="1")


def test_left_fmap_returns_left_unchanged_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> str:
        calls.append(a)
        return str(a)

    left: Either[str, int] = Left(value="boom")
    assert left.fmap(f) == Left(value="boom")
    assert calls == []


def test_free_fmap_delegates_to_the_method_for_left() -> None:
    left: Either[str, int] = Left(value="boom")
    assert fmap(str, left) == Left(value="boom")


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(Right, st.integers())


def test_abstract_fmap_raises_if_not_overridden() -> None:
    right: Right[str, int] = Right(value=1)
    with pytest.raises(NotImplementedError):
        Either.fmap(right, str)


def test_point_constructs_a_right_wrapping_the_value() -> None:
    assert Either.point(1) == Right(value=1)


def test_point_then_fmap_chains_correctly() -> None:
    assert Either.point(1).fmap(str) == Right(value="1")


def test_right_ap_applies_the_wrapped_function() -> None:
    wrapped_fn: Either[str, Callable[[int], str]] = Right(value=str)
    right: Right[str, int] = Right(value=5)
    assert right.ap(wrapped_fn) == Right(value="5")


def test_right_ap_with_left_function_returns_that_left() -> None:
    wrapped_fn: Either[str, Callable[[int], str]] = Left(value="boom")
    right: Right[str, int] = Right(value=5)
    assert right.ap(wrapped_fn) == Left(value="boom")


def test_left_ap_returns_left_unchanged_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> str:
        calls.append(a)
        return str(a)

    wrapped_fn: Either[str, Callable[[int], str]] = Right(value=f)
    left: Either[str, int] = Left(value="boom")
    assert left.ap(wrapped_fn) == Left(value="boom")
    assert calls == []


def test_free_ap_delegates_to_the_method() -> None:
    wrapped_fn: Either[str, Callable[[int], str]] = Right(value=str)
    assert ap(wrapped_fn, Right(value=5)) == Right(value="5")


def test_satisfies_the_apply_law() -> None:
    assert_apply_law(Right, st.integers())


def test_is_an_applicative() -> None:
    assert isinstance(Right(value=1), Applicative)
    left: Either[str, int] = Left(value="boom")
    assert isinstance(left, Applicative)


def test_satisfies_the_applicative_laws() -> None:
    assert_applicative_law(Either.point, st.integers())


def test_abstract_ap_raises_if_not_overridden() -> None:
    right: Right[str, int] = Right(value=1)
    wrapped_fn: Either[str, Callable[[int], str]] = Right(value=str)
    with pytest.raises(NotImplementedError):
        Either.ap(right, wrapped_fn)


def test_right_ap_raises_for_an_unrecognized_either_subclass() -> None:
    rogue: Either[str, Callable[[int], str]] = _RogueEither()
    right: Right[str, int] = Right(value=1)
    with pytest.raises(AssertionError):
        right.ap(rogue)


def test_right_bind_applies_f_and_flattens() -> None:
    right: Right[str, int] = Right(value=5)
    assert right.bind(lambda a: Right(value=str(a))) == Right(value="5")


def test_right_bind_with_f_returning_left() -> None:
    def f(a: int) -> "Either[str, str]":
        return Left(value="boom")

    right: Right[str, int] = Right(value=5)
    assert right.bind(f) == Left(value="boom")


def test_left_bind_returns_left_unchanged_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> "Either[str, str]":
        calls.append(a)
        return Right(value=str(a))

    left: Either[str, int] = Left(value="boom")
    assert left.bind(f) == Left(value="boom")
    assert calls == []


def test_free_bind_delegates_to_the_method() -> None:
    assert bind(lambda a: Right(value=str(a)), Right(value=5)) == Right(value="5")


def test_is_a_bind() -> None:
    assert isinstance(Right(value=5), Bind)
    left: Either[str, int] = Left(value="boom")
    assert isinstance(left, Bind)


def test_satisfies_the_bind_law() -> None:
    assert_bind_law(Right, st.integers())


def test_abstract_bind_raises_if_not_overridden() -> None:
    right: Right[str, int] = Right(value=1)
    with pytest.raises(NotImplementedError):
        Either.bind(right, lambda a: Right(value=a))


def test_right_bind_raises_for_an_unrecognized_either_subclass() -> None:
    def f(a: int) -> "Either[str, str]":
        return _RogueEither()

    right: Right[str, int] = Right(value=1)
    with pytest.raises(AssertionError):
        right.bind(f)


def test_is_a_monad() -> None:
    assert isinstance(Right(value=1), Monad)
    left: Either[str, int] = Left(value="boom")
    assert isinstance(left, Monad)


def test_satisfies_the_monad_law() -> None:
    assert_monad_law(Either.point, st.integers())


def _describe(e: "Union[Left[str, int], Right[str, int]]") -> str:
    # No fallback `case _:` -- this is only exhaustive, and therefore
    # only type-checks under `mypy --strict`, because `e` is typed as
    # the Union of both variants rather than the abstract Either[str, int].
    match e:
        case Left(value=lv):
            return f"error: {lv}"
        case Right(value=rv):
            return f"ok: {rv}"


def test_match_case_is_exhaustive_over_right() -> None:
    assert _describe(Right(value=5)) == "ok: 5"


def test_match_case_is_exhaustive_over_left() -> None:
    assert _describe(Left(value="boom")) == "error: boom"


@given(st.integers())
def test_match_case_narrows_rights_value_precisely(value: int) -> None:
    assert _describe(Right(value=value)) == f"ok: {value}"
