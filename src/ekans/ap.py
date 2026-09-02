"""Ap: a Semigroup wrapper deriving mappend from an Applicative via liftA2.

Fixed to wrap Identity[S] specifically, not generic over an arbitrary
Applicative F -- Python has no higher-kinded types (verified in Phase 1:
Generic[F, A] with a field typed F[A] where F is a bare TypeVar is a
hard mypy error).
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

from ekans.applicative import liftA2
from ekans.extractable import Extractable
from ekans.identity import Identity
from ekans.semigroup import Semigroup

S = TypeVar("S", bound=Semigroup)


@dataclass(frozen=True, eq=False)
class Ap(Semigroup, Extractable[S], Generic[S]):
    """Wraps an Identity[S], combining two via liftA2's lifted mappend.

    A faithful (if narrower) transcription of Haskell's
    `newtype Ap f a = Ap { getAp :: f a }`, fixed here to
    `f = Identity` since Python can't express "any Applicative f"
    generically.

    Attributes:
        value: The wrapped Identity, holding a Semigroup value.
    """

    value: Identity[S]

    def mappend(self, other: "Ap[S]") -> "Ap[S]":
        """Combine `self` with `other` via `liftA2` over the wrapped Identity.

        Args:
            other: Another Ap wrapping an Identity of the same type.

        Returns:
            A new Ap wrapping `liftA2(mappend, self.value, other.value)`.
        """
        return Ap(value=liftA2(lambda a, b: a.mappend(b), self.value, other.value))

    # mypy treats narrowing __eq__'s parameter away from `object` as an
    # LSP violation ([override]); that narrowing is exactly the point here.
    def __eq__(self, other: "Ap[S]") -> bool:  # type: ignore[override]
        """Compare against another Ap wrapping the same type.

        Args:
            other: Another Ap wrapping the same type of value.

        Returns:
            Whether the wrapped Identities are equal, or
            ``NotImplemented`` if `other` isn't an Ap at all.
        """
        if not isinstance(other, Ap):
            return NotImplemented
        return bool(self.value == other.value)

    def __hash__(self) -> int:
        """Hash consistently with equality, based on the wrapped Identity.

        Returns:
            The hash of the wrapped Identity.
        """
        return hash(self.value)

    def extract(self) -> S:
        """Return the fully unwrapped held value.

        Delegates to the wrapped Identity's own `extract`, so this
        returns `S` directly rather than the intermediate `Identity[S]`
        -- Identity wrapping S here is an implementation detail forced
        by Python's lack of higher-kinded types, not something a
        caller of extract should have to peel back themselves.

        Returns:
            The fully unwrapped held value.
        """
        return self.value.extract()
