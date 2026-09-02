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
from ekans.functor import fmap
from ekans.maybe import Just, Maybe, Nothing
from ekans.monad import Monad

_A = TypeVar("_A")
_B = TypeVar("_B")


@dataclass(frozen=True, eq=False)
class _RogueMaybe(Maybe[_A], Generic[_A]):
    """A third Maybe variant, existing only to prove the `ap`/`bind`
    `case _: raise AssertionError` fallback (docs/specs/maybe.md's
    Design section) is a real safety net, not dead code -- mypy can't
    prove a match over the abstract Maybe handle is exhaustive, so
    both methods guard against exactly this kind of unrecognized
    subclass at runtime.
    """

    def fmap(self, f: Callable[[_A], _B]) -> "Just[_B]":
        raise NotImplementedError

    def ap(  # type: ignore[override]
        self, f: "Maybe[Callable[[_A], _B]]"
    ) -> "Union[Just[_B], Nothing[_B]]":
        raise NotImplementedError

    def bind(  # type: ignore[override]
        self, f: Callable[[_A], "Maybe[_B]"]
    ) -> "Union[Just[_B], Nothing[_B]]":
        raise NotImplementedError

    def __eq__(self, other: "Maybe[_A]") -> bool:  # type: ignore[override]
        return isinstance(other, _RogueMaybe)

    def __hash__(self) -> int:
        return 0


def test_just_holds_the_value() -> None:
    assert Just(value=1).value == 1


def test_just_equal_when_values_are_equal() -> None:
    assert Just(value=1) == Just(value=1)


def test_just_not_equal_when_values_differ() -> None:
    assert Just(value=1) != Just(value=2)


def test_nothing_equal_to_nothing() -> None:
    a: Maybe[int] = Nothing()
    b: Maybe[int] = Nothing()
    assert a == b


def test_just_not_equal_to_nothing() -> None:
    just: Maybe[int] = Just(value=1)
    nothing: Maybe[int] = Nothing()
    assert just != nothing
    assert nothing != just


def test_not_equal_to_an_unrelated_type() -> None:
    assert Just(value=1) != "not a Maybe"
    assert Nothing[int]() != "not a Maybe"


def test_just_equal_values_hash_the_same() -> None:
    assert hash(Just(value=1)) == hash(Just(value=1))


def test_nothing_instances_hash_the_same() -> None:
    assert hash(Nothing[int]()) == hash(Nothing[str]())


def test_is_usable_as_a_set_member() -> None:
    assert {Just(value=1), Just(value=1), Just(value=2)} == {
        Just(value=1),
        Just(value=2),
    }


def test_just_is_immutable() -> None:
    just = Just(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        just.value = 2  # type: ignore[misc]


def test_nothing_is_immutable() -> None:
    nothing: Maybe[int] = Nothing()
    with pytest.raises(AttributeError):
        nothing.extra = 2


def test_just_fmap_applies_the_function_to_the_wrapped_value() -> None:
    assert Just(value=1).fmap(str) == Just(value="1")


def test_free_fmap_delegates_to_the_method_for_just() -> None:
    assert fmap(str, Just(value=1)) == Just(value="1")


def test_nothing_fmap_returns_nothing_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> str:
        calls.append(a)
        return str(a)

    nothing: Maybe[int] = Nothing()
    assert nothing.fmap(f) == Nothing()
    assert calls == []


def test_free_fmap_delegates_to_the_method_for_nothing() -> None:
    nothing: Maybe[int] = Nothing()
    assert fmap(str, nothing) == Nothing()


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(Just, st.integers())


def test_abstract_fmap_raises_if_not_overridden() -> None:
    just = Just(value=1)
    with pytest.raises(NotImplementedError):
        Maybe.fmap(just, str)


def test_point_constructs_a_just_wrapping_the_value() -> None:
    assert Maybe.point(1) == Just(value=1)


def test_point_then_fmap_chains_correctly() -> None:
    assert Maybe.point(1).fmap(str) == Just(value="1")


def test_just_ap_applies_the_wrapped_function() -> None:
    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=str)
    assert Just(value=5).ap(wrapped_fn) == Just(value="5")


def test_just_ap_with_nothing_function_returns_nothing() -> None:
    wrapped_fn: Maybe[Callable[[int], str]] = Nothing()
    assert Just(value=5).ap(wrapped_fn) == Nothing()


def test_nothing_ap_returns_nothing_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> str:
        calls.append(a)
        return str(a)

    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=f)
    nothing: Maybe[int] = Nothing()
    assert nothing.ap(wrapped_fn) == Nothing()
    assert calls == []


def test_free_ap_delegates_to_the_method() -> None:
    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=str)
    assert ap(wrapped_fn, Just(value=5)) == Just(value="5")


def test_satisfies_the_apply_law() -> None:
    assert_apply_law(Just, st.integers())


def test_abstract_ap_raises_if_not_overridden() -> None:
    just = Just(value=1)
    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=str)
    with pytest.raises(NotImplementedError):
        Maybe.ap(just, wrapped_fn)


def test_just_ap_raises_for_an_unrecognized_maybe_subclass() -> None:
    rogue: Maybe[Callable[[int], str]] = _RogueMaybe()
    with pytest.raises(AssertionError):
        Just(value=1).ap(rogue)


def test_is_an_applicative() -> None:
    assert isinstance(Just(value=1), Applicative)
    nothing: Maybe[int] = Nothing()
    assert isinstance(nothing, Applicative)


def test_satisfies_the_applicative_laws() -> None:
    assert_applicative_law(Maybe.point, st.integers())


def test_just_bind_applies_f_and_flattens() -> None:
    assert Just(value=5).bind(lambda a: Just(value=str(a))) == Just(value="5")


def test_just_bind_with_f_returning_nothing() -> None:
    def f(a: int) -> "Maybe[str]":
        return Nothing()

    assert Just(value=5).bind(f) == Nothing()


def test_nothing_bind_returns_nothing_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> "Maybe[str]":
        calls.append(a)
        return Just(value=str(a))

    nothing: Maybe[int] = Nothing()
    assert nothing.bind(f) == Nothing()
    assert calls == []


def test_free_bind_delegates_to_the_method() -> None:
    assert bind(lambda a: Just(value=str(a)), Just(value=5)) == Just(value="5")


def test_is_a_bind() -> None:
    assert isinstance(Just(value=5), Bind)
    nothing: Maybe[int] = Nothing()
    assert isinstance(nothing, Bind)


def test_satisfies_the_bind_law() -> None:
    assert_bind_law(Just, st.integers())


def test_abstract_bind_raises_if_not_overridden() -> None:
    just = Just(value=1)
    with pytest.raises(NotImplementedError):
        Maybe.bind(just, lambda a: Just(value=a))


def test_just_bind_raises_for_an_unrecognized_maybe_subclass() -> None:
    def f(a: int) -> "Maybe[str]":
        return _RogueMaybe()

    with pytest.raises(AssertionError):
        Just(value=1).bind(f)


def test_is_a_monad() -> None:
    assert isinstance(Just(value=1), Monad)
    nothing: Maybe[int] = Nothing()
    assert isinstance(nothing, Monad)


def test_satisfies_the_monad_law() -> None:
    assert_monad_law(Maybe.point, st.integers())


def _describe(m: "Union[Just[int], Nothing[int]]") -> str:
    # No fallback `case _:` -- this is only exhaustive, and therefore
    # only type-checks under `mypy --strict`, because `m` is typed as
    # the Union of both variants rather than the abstract Maybe[int].
    match m:
        case Just(value=v):
            return f"got {v}"
        case Nothing():
            return "nothing"


def test_match_case_is_exhaustive_over_just() -> None:
    assert _describe(Just(value=5)) == "got 5"


def test_match_case_is_exhaustive_over_nothing() -> None:
    assert _describe(Nothing()) == "nothing"


@given(st.integers())
def test_match_case_narrows_justs_value_precisely(value: int) -> None:
    assert _describe(Just(value=value)) == f"got {value}"
