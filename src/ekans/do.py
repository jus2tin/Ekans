"""@do: flatten Monad bind chains into linear, generator-based code."""

from typing import Any, Callable, Generator, ParamSpec, TypeVar

from ekans.monad import Monad

P = ParamSpec("P")
T = TypeVar("T")
U = TypeVar("U")


def do(fn: Callable[P, Generator[Monad[T], Any, Monad[U]]]) -> Callable[P, Monad[U]]:
    """Flatten a generator yielding Monads into one chained bind computation.

    The decorated function must `yield` Monad values and annotate its own
    return type as `Generator[Monad[T], Any, Monad[U]]`; every `yield`
    assignment inside it must carry an explicit local type annotation
    (e.g. `a: int = yield container`) to recover real type-checking for
    that name -- see docs/HOWTO.md's `@do` section for why this is
    required, not optional.

    Args:
        fn: A generator function that yields Monad values and returns a
            final Monad, matching the do-notation shape described above.

    Returns:
        A function with the same parameters as `fn`, returning the
        single Monad produced by chaining every yielded Monad's `bind`
        together.
    """

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Monad[U]:
        gen = fn(*args, **kwargs)

        def step(val: Any = None) -> Monad[U]:
            try:
                m = gen.send(val)
            except StopIteration as e:
                # StopIteration.value is typeshed-Any -- the runtime
                # return value of an arbitrary user generator, genuinely
                # untyped at this boundary; no narrower type is derivable.
                return e.value  # type: ignore[no-any-return]
            return m.bind(step)

        try:
            initial_m = next(gen)
        except StopIteration as e:
            return e.value  # type: ignore[no-any-return]

        return initial_m.bind(step)

    return wrapper
