"""Ekans: pure functional primitives for Python.

Curated re-exports of the public type hierarchy and its free functions.
Internal to this module: a handful of free functions share a name with
an existing submodule (`ap`, `bind`, `do`, `all`, `sum`, `product`,
`const`) -- re-exporting those bare names here would make `ekans.<name>`
resolve inconsistently depending on unrelated import order elsewhere in
a program, since Python rebinds a package attribute to the submodule
itself every time that submodule is imported anywhere. Those stay
reachable only via their fully-qualified submodule path (e.g.
`from ekans.foldable import sum`), matching every example already in
`docs/HOWTO.md`.
"""

from ekans.all import All
from ekans.ap import Ap
from ekans.applicative import Applicative, liftA2
from ekans.apply import Apply
from ekans.bind import Bind
from ekans.const import Const
from ekans.either import Either, Left, Right
from ekans.extractable import Extractable
from ekans.foldable import (
    Foldable,
    FoldableABC,
    SupportsLt,
    and_,
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
    toList,
)
from ekans.functional import Functional
from ekans.functor import Functor, fmap
from ekans.identity import Identity
from ekans.maybe import Just, Maybe, Nothing
from ekans.monad import Monad
from ekans.monoid import Monoid
from ekans.pointed import Pointed
from ekans.product import Product, SupportsMul, SupportsOne
from ekans.reader import Reader
from ekans.semigroup import Semigroup, mappend
from ekans.sum import Sum, SupportsAdd, SupportsZero
from ekans.tuple2 import Tuple2

__all__ = [
    "All",
    "Ap",
    "Applicative",
    "liftA2",
    "Apply",
    "Bind",
    "Const",
    "Either",
    "Left",
    "Right",
    "Extractable",
    "Foldable",
    "FoldableABC",
    "SupportsLt",
    "and_",
    "concat",
    "concatMap",
    "elem",
    "find",
    "fold",
    "fold1",
    "foldl",
    "foldl1",
    "foldMap",
    "foldr",
    "foldr1",
    "length",
    "maximum",
    "maximumBy",
    "minimum",
    "minimumBy",
    "notElem",
    "null",
    "or_",
    "toList",
    "Functional",
    "Functor",
    "fmap",
    "Identity",
    "Just",
    "Maybe",
    "Nothing",
    "Monad",
    "Monoid",
    "Pointed",
    "Product",
    "SupportsMul",
    "SupportsOne",
    "Reader",
    "Semigroup",
    "mappend",
    "Sum",
    "SupportsAdd",
    "SupportsZero",
    "Tuple2",
]
