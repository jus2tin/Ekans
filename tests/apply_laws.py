"""Reusable Hypothesis-based Apply law check.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/apply.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ekans.apply import Apply

A = TypeVar("A")


def _identity(a: A) -> A:
    return a


def _compose(g: Callable[[A], A]) -> Callable[[Callable[[A], A]], Callable[[A], A]]:
    """Typed stand-in for a composition-building lambda.

    `st.functions(like=...)` needs an annotated callable to infer the
    generated functions' signature from, same reasoning as
    `functor_laws.py`'s `_identity`.

    Args:
        g: The outer function in the composition.

    Returns:
        A function that, given `f`, returns the composition `g after f`.
    """

    def _compose_with(f: Callable[[A], A]) -> Callable[[A], A]:
        def _composed(a: A) -> A:
            return g(f(a))

        return _composed

    return _compose_with


def assert_apply_law(
    make: Callable[[A], Apply[A]],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Apply[A], Apply[A]], bool]] = None,
) -> None:
    """Assert the Apply associativity law for `make`.

    Args:
        make: Constructs an Apply instance wrapping a given value.
        values: A Hypothesis strategy generating values to wrap.
        equal: How to compare two Apply instances for the purpose of
            the law below. Defaults to `==`. Pass this when the Apply
            wraps something without meaningful structural equality
            (e.g. a function) -- same reasoning as
            `functor_laws.assert_functor_laws`'s `equal` parameter.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    @given(
        values,
        st.functions(like=_identity, returns=values, pure=True),
        st.functions(like=_identity, returns=values, pure=True),
    )
    def associativity_law(value: A, f: Callable[[A], A], g: Callable[[A], A]) -> None:
        w = make(value)
        # `make` is typed Callable[[A], Apply[A]] to wrap plain values
        # (per the approved signature, matching assert_functor_laws'
        # `make`) -- reusing it here to wrap *functions* instead is a
        # deliberate, understood mismatch the type system can't
        # express without a rank-2 Protocol more complex than what
        # was approved for this helper; the explicit annotations
        # correct the type mypy would otherwise infer from `make`'s
        # declared (wrong-for-this-call) return type -- mypy reports
        # this as both an argument mismatch and an assignment mismatch
        # simultaneously ([arg-type, assignment]).
        v: Apply[Callable[[A], A]] = make(f)  # type: ignore[arg-type, assignment]
        u: Apply[Callable[[A], A]] = make(g)  # type: ignore[arg-type, assignment]
        lhs = w.ap(v.ap(u.fmap(_compose)))
        rhs = w.ap(v).ap(u)
        assert eq(lhs, rhs)

    associativity_law()
