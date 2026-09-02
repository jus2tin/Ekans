"""Tuple2: a pair, Functor/Extractable biased to the second slot."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Type, TypeVar

from ekans.extractable import Extractable
from ekans.functor import Functor

if TYPE_CHECKING:
    from ekans.monoid import Monoid

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
S = TypeVar("S", bound="Monoid")
MA = TypeVar("MA", bound="Monoid")
MB = TypeVar("MB", bound="Monoid")


@dataclass(frozen=True, eq=False)
class Tuple2(Functor[B], Extractable[B], Generic[A, B]):
    """A pair: holds a real `A` and a real `B`.

    `Functor`/`Extractable` are biased to `B`, matching `Const`'s own
    bias -- `A` is untouched by `fmap`.

    Attributes:
        first: The value `fmap` never touches.
        second: The value `fmap`/`extract` operate on.
    """

    first: A
    second: B

    def fmap(self, f: Callable[[B], C]) -> "Tuple2[A, C]":
        """Apply `f` to `second`, leaving `first` untouched.

        Args:
            f: The function to apply to `second`.

        Returns:
            A new Tuple2 with the same `first`, `second` mapped by `f`.
        """
        return Tuple2(first=self.first, second=f(self.second))

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Tuple2[A, B]") -> bool:  # type: ignore[override]
        """Compare against another Tuple2 wrapping the same types.

        Typed against ``Tuple2[A, B]`` rather than ``object`` so that
        mypy rejects comparisons between differently-parameterized
        Tuple2 instances in either type parameter, at type-check time.

        Args:
            other: Another Tuple2 with the same A and B.

        Returns:
            Whether both held values are equal, or ``NotImplemented``
            if `other` isn't a Tuple2 at all.
        """
        if not isinstance(other, Tuple2):
            return NotImplemented
        return bool(self.first == other.first) and bool(self.second == other.second)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on both held values.

        Returns:
            The hash of `(first, second)`.
        """
        return hash((self.first, self.second))

    def extract(self) -> B:
        """Return `second`.

        Returns:
            The wrapped second value.
        """
        return self.second

    @classmethod
    def point(cls, value_type: Type[S], value: B) -> "Tuple2[S, B]":
        """Construct a Tuple2 pairing `value_type`'s identity with `value`.

        Unlike `Const.point`, `value` is genuinely used here, not
        discarded -- `pure x = (mempty, x)`.

        Args:
            value_type: The concrete Monoid type for `first`.
            value: The value to pair it with, held in `second`.

        Returns:
            `Tuple2(first=value_type.mempty(), second=value)`.
        """
        return Tuple2(first=value_type.mempty(), second=value)

    @classmethod
    def mempty(cls, a_type: Type[MA], b_type: Type[MB]) -> "Tuple2[MA, MB]":
        """Construct the identity element, pointwise.

        Needs both `a_type` and `b_type` to independently satisfy
        `Monoid` -- the first pattern in this codebase requiring two
        independent bounds at once rather than one.

        Args:
            a_type: The concrete Monoid type for `first`.
            b_type: The concrete Monoid type for `second`.

        Returns:
            `Tuple2(first=a_type.mempty(), second=b_type.mempty())`.
        """
        return Tuple2(first=a_type.mempty(), second=b_type.mempty())
