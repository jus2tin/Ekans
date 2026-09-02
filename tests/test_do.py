from dataclasses import dataclass
from typing import Any, Callable, Generator, Generic, TypeVar

from hypothesis import given
from hypothesis import strategies as st

from ekans.do import do
from ekans.identity import Identity
from ekans.maybe import Just, Nothing
from ekans.monad import Monad
from ekans.reader import Reader

A = TypeVar("A")
B = TypeVar("B")


@given(st.integers(), st.integers())
def test_do_matches_manual_bind_chaining_for_identity(x: int, y: int) -> None:
    @do
    def computation() -> Generator[Monad[int], Any, Monad[int]]:
        a: int = yield Identity(value=x)
        b: int = yield Identity(value=y)
        return Identity(value=a + b)

    manual = Identity(value=x).bind(
        lambda a: Identity(value=y).bind(lambda b: Identity(value=a + b))
    )
    assert computation() == manual


@given(st.integers(), st.integers(), st.integers())
def test_do_matches_manual_bind_chaining_for_reader(env: int, x: int, y: int) -> None:
    @do
    def computation() -> Generator[Monad[int], Any, Monad[int]]:
        a: int = yield Reader(run=lambda r: r + x)
        b: int = yield Reader(run=lambda r: r + y)
        return Reader(run=lambda r: a + b)

    manual: Reader[int, int] = Reader(run=lambda r: r + x).bind(
        lambda a: Reader(run=lambda r: r + y).bind(
            lambda b: Reader(run=lambda r: a + b)
        )
    )

    result = computation()
    assert isinstance(result, Reader) and isinstance(manual, Reader)
    assert result.run(env) == manual.run(env)


@given(st.integers())
def test_do_handles_a_generator_that_never_yields(value: int) -> None:
    @do
    def computation() -> Generator[Monad[int], Any, Monad[int]]:
        return Identity(value=value)
        yield  # unreachable -- makes this a generator function syntactically

    assert computation() == Identity(value=value)


call_log: list[str] = []


@dataclass(frozen=True, eq=False)
class _Nothing(Monad[A], Generic[A]):
    """A local, test-only short-circuiting Monad double.

    Not exported -- Ekans has no shipped Maybe/Either yet (see
    docs/specs/do.md's Out of scope section). Mirrors
    tests/test_monad.py's illustrative-type convention.
    """

    def fmap(self, f: Callable[[A], B]) -> "_Nothing[B]":
        return _Nothing()

    @classmethod
    def point(cls, value: A) -> "_Nothing[A]":  # type: ignore[override]
        return _Nothing()

    def ap(  # type: ignore[override]
        self, f: "_Nothing[Callable[[A], B]]"
    ) -> "_Nothing[B]":
        return _Nothing()

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "Monad[B]"]
    ) -> "_Nothing[B]":
        call_log.append("Nothing.bind: not calling f")
        return _Nothing()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Nothing)

    def __hash__(self) -> int:
        return 0


@dataclass(frozen=True, eq=False)
class _Just(Monad[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_Just[B]":
        return _Just(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "_Just[A]":  # type: ignore[override]
        return _Just(value=value)

    def ap(self, f: "_Just[Callable[[A], B]]") -> "_Just[B]":  # type: ignore[override]
        return _Just(value=f.value(self.value))

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "Monad[B]"]
    ) -> "Monad[B]":
        call_log.append(f"Just.bind: calling f({self.value!r})")
        return f(self.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Just) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_do_short_circuits_and_never_resumes_past_a_nothing() -> None:
    call_log.clear()

    @do
    def computation() -> Generator[Monad[int], Any, Monad[int]]:
        a: int = yield _Just(value=1)
        call_log.append(f"got a={a!r}")
        b: int = yield _Nothing()
        call_log.append("SHOULD NOT REACH HERE")
        return _Just(value=a + b)

    result = computation()

    assert result == _Nothing()
    assert "SHOULD NOT REACH HERE" not in call_log
    assert call_log == [
        "Just.bind: calling f(1)",
        "got a=1",
        "Nothing.bind: not calling f",
    ]


def test_do_short_circuits_with_the_real_maybe_type() -> None:
    # Regression test against the shipped Maybe type, per
    # docs/specs/do.md's own flagged follow-up -- the local _Just/
    # _Nothing double above stays too, since the do-notation guarantee
    # is generic over any Monad, not Maybe-specific.
    reached_past_nothing = []

    @do
    def computation() -> Generator[Monad[int], Any, Monad[int]]:
        a: int = yield Just(value=1)
        b: int = yield Nothing()
        reached_past_nothing.append(True)
        return Just(value=a + b)

    result = computation()

    assert result == Nothing()
    assert reached_past_nothing == []
