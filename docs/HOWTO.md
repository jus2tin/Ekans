# The Ekans How-To

*A field guide to growing pure functional types in Python, one small abstract class at a time.*

This is a single article for now. As the library grows, the sections below are written to stand on their own — each one explains its concept without leaning on the sections after it — so that one day they can be lifted out into their own pages, wiki-style, without anyone having to rewrite a word. Until then: one file, scroll away.

Every concept, type, and function that exists in the package gets a section here. The ones that don't exist *yet* get a stub, so you can see the whole shape of where this is headed.

## Contents

- [Functional: the box with a broken lid](#functional-the-box-with-a-broken-lid)
- [Identity: the box that changes nothing](#identity-the-box-that-changes-nothing)
- [Functor: doing something to what's inside](#functor-doing-something-to-whats-inside)
- [Const: the box that refuses to look](#const-the-box-that-refuses-to-look)
- [Pointed: getting a value into a box](#pointed-getting-a-value-into-a-box)
- [Reader: a box that's actually a function](#reader-a-box-thats-actually-a-function)
- [Apply: when the function is also in a box](#apply-when-the-function-is-also-in-a-box)
- [Applicative: Pointed and Apply, together](#applicative-pointed-and-apply-together)
- [Semigroup: squishing two into one](#semigroup-squishing-two-into-one)
- [Sum: addition, boxed](#sum-addition-boxed)
- [Product: multiplication, boxed](#product-multiplication-boxed)
- [All: everyone has to agree](#all-everyone-has-to-agree)
- [Ap: a box, held by a box](#ap-a-box-held-by-a-box)
- [Extractable: getting a value out of a box](#extractable-getting-a-value-out-of-a-box)
- [Monoid: something out of nothing](#monoid-something-out-of-nothing)
- [Bind: chaining boxes without nesting them](#bind-chaining-boxes-without-nesting-them)
- [Monad: Applicative and Bind, evolved](#monad-applicative-and-bind-evolved)
- [Coming soon](#coming-soon)

## Functional: the box with a broken lid

Every type in Ekans starts life by inheriting from `Functional`. It doesn't do much — which is exactly the point. All it does is refuse to let anyone change it after it's built:

```python
from ekans.functional import Functional

box = Functional()
box.anything = 1
# Traceback (most recent call last):
#   ...
# AttributeError: Functional is immutable: cannot set 'anything'
```

That's the entire theory behind this one: **pure functions don't get surprised**. A pure function's whole deal is that if you call it twice with the same input, you get the same output, every time, forever. That guarantee quietly falls apart the moment something *else* is allowed to reach into your data and change it behind your back — mid-computation, from another thread, from a function three calls up the stack you forgot could see this object. `Functional` makes that impossible at the language level instead of asking you to promise not to do it.

In practice, you won't build bare `Functional` instances like the one above. You'll build concrete types as **frozen dataclasses** that inherit from `Functional`:

```python
from dataclasses import dataclass
from ekans.functional import Functional

@dataclass(frozen=True)
class Point(Functional):
    x: int
    y: int

p = Point(x=1, y=2)
p.x  # 1

p.x = 99
# Traceback (most recent call last):
#   ...
# dataclasses.FrozenInstanceError: cannot assign to field 'x'
```

Here's the fun detail: notice the exception is `FrozenInstanceError`, not the `AttributeError` from the first example, and the message is different too ("cannot assign to field" vs. "is immutable: cannot set"). That's because `@dataclass(frozen=True)` politely writes its *own* `__setattr__` directly onto `Point`, and Python finds that one first — it never even asks `Functional`. So which lock actually stops you depends on whether the class in question is a frozen dataclass.

Is that a bug? No — `FrozenInstanceError` is a subclass of `AttributeError` (check `isinstance(err, AttributeError)` — it's `True`), so as far as anyone catching exceptions is concerned, the contract holds either way. Think of it as two independent locks on the same door: the dataclass's lock is the one you'll usually feel, and `Functional`'s lock is the backup that still catches you if a concrete type is ever *not* built as a frozen dataclass (a plain class with a hand-written `__init__`, say). Belt, suspenders, immutable data.

## Identity: the box that changes nothing

`Identity[A]` is the simplest possible box: it holds exactly one value of type `A`, and does nothing clever with it whatsoever.

```python
from ekans.identity import Identity

box = Identity(value=42)
box.value  # 42

Identity(value=1) == Identity(value=1)  # True — same value in, same box out

box.value = 7
# Traceback (most recent call last):
#   ...
# dataclasses.FrozenInstanceError: cannot assign to field 'value'
```

In Haskell this is `newtype Identity a = Identity a` — a type that exists almost entirely to prove a point. `Identity` is the textbook `Functor` (see that section below): calling `box.fmap(str)` turns `Identity(value=42)` into `Identity(value="42")` — same box, transformed insides, nothing else disturbed:

```python
box = Identity(value=42)
box.fmap(str)  # Identity(value='42')

from ekans.functor import fmap
fmap(str, box)  # Identity(value='42') -- same thing, free-function form
```

That's the whole idea of a functor in one sentence: **change what's inside without changing the shape of the container.** `Identity` is the functor that changes the *least* — it's the control group: it's also `Identity`, not some illustrative stand-in, that every `Functor` law gets checked against first for exactly that reason — if a law doesn't hold for the box that does nothing, it isn't going to hold for anything fancier either.

**A fun wrinkle: equality has a type, too.** In Haskell, `Identity 1 == Identity "a"` isn't a bug you catch at runtime — the compiler refuses to build it, because `Eq (Identity a)` only exists for a given `a`, and `Int` isn't `String`. Ekans gets the same guarantee, just enforced by mypy instead of `ghc`:

```python
a: Identity[int] = Identity(value=1)
b: Identity[str] = Identity(value="not an int")

a == b
# error: Unsupported operand types for == ("Identity[int]" and "Identity[str]")  [operator]
```

That happens because `Identity.__eq__` is typed against `Identity[A]` — the same `A` as `self` — instead of the usual `object`. It costs a `# type: ignore[override]` on the definition (mypy considers narrowing `__eq__`'s parameter an LSP violation, and normally it's right to complain — here it's exactly the point). Comparing to something that isn't an `Identity` at all, like `Identity(value=1) == 5`, still type-checks fine and is just `False` at runtime, same as ordinary Python — only *same-class-different-type-parameter* comparisons get turned into an error.

`Identity` is also the first type shipped in the package to actually implement `Pointed` (see that section below): `Identity.point(5)` builds `Identity(value=5)` directly, no instance required to call it on:

```python
Identity.point(5)  # Identity(value=5)
Identity.point(5).fmap(str)  # Identity(value='5') -- point and fmap chain fine
```

`Identity` is also the first shipped `Apply` instance (see that section below): `.ap` unwraps both boxes and applies one to the other —

```python
wrapped_fn: Identity[Callable[[int], str]] = Identity(value=str)
Identity(value=5).ap(wrapped_fn)  # Identity(value='5')
```

Since `Identity` has both `point` and `ap`, it's an `Applicative` too (see that section below) — nothing extra to write, `point`/`ap`/`fmap` already do all the work.

`Identity` also has `bind` (see the `Bind` section below): `Identity(value=5).bind(lambda a: Identity(value=str(a)))` gives `Identity(value='5')` — no nesting, since `bind` un-nests automatically where `fmap` wouldn't. With both `Applicative` and `Bind` in hand, `Identity` is a `Monad` too (see that section below), for free — `class Identity(Monad[A], Extractable[A], Generic[A])` is the whole story, same zero-effort composition `Applicative` already demonstrated for `Pointed` + `Apply`.

**Conditionally a `Semigroup`, but only via the free function.** `Identity[A]` can `mappend` two of itself precisely when `A` can — `Identity(value=1)` and `Identity(value=2)` combine fine if the wrapped value knows how, but there's no principled way to combine `Identity(value="a")` and `Identity(value="b")` unless `str` itself is a `Semigroup` (it isn't, here). Because that constraint lives on `A`, not on `Identity` itself, `Identity` never nominally inherits `Semigroup` — instead, `ekans.semigroup.mappend(a, b)` is a free function bounded by `TypeVar("S", bound=Semigroup)`, so calling it on `Identity[str]` is a `mypy --strict` error, not a runtime crash. See the `Semigroup` section below for the full story.

`Identity` is also `Extractable` (see that section below) — `Identity(value=5).extract()` just returns `5`. For `Identity` specifically this is barely more than `.value` with extra ceremony, but it's the same uniform `extract` every other single-value type in the package shares, and `Identity` is the simplest possible place to see it work.

`Identity.mempty(SomeMonoidType)` builds the identity element, wrapped: `Identity.mempty(Box)` gives `Identity(value=Box.mempty())`. Same non-nominal story as `Identity`'s `Semigroup` support (see the `Monoid` section below) — but unlike `mappend`, this one's a classmethod directly on `Identity`, not a free function, since a classmethod's own `TypeVar` doesn't leak onto every `Identity[A]` the way a nominal instance method would.

## Functor: doing something to what's inside

`Functor` is the first real capability in the hierarchy — everything before it (`Functional`, `Identity`) was about being an honest, immutable box. `Functor` is about doing something *to* what's in the box, without disturbing the box itself.

Concretely: a `Functor[A]` gives you one operation, `fmap`, which takes a function `A -> B` and hands back the same kind of container, now holding a `B` instead of an `A`.

```python
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.functor import Functor, fmap

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Box(Functor[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "Box[B]":
        return Box(value=f(self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


Box(value=5).fmap(str)   # Box(value='5')
fmap(str, Box(value=5))  # Box(value='5') -- same thing, free-function form
```

Both spellings do the same thing — `box.fmap(f)` and `fmap(f, box)` — pick whichever reads better at the call site. `Box` here is a stand-in for illustration; `Identity` (see its section above) is the real, shipped example, and its `fmap` is exactly this shape.

**Two rules, not just a vibe.** For `fmap` to actually deserve the name "functor," it has to satisfy two laws, for every `Functor` type, forever:

1. **Mapping with a do-nothing function does nothing.** `box.fmap(lambda a: a) == box`. If an `fmap` implementation somehow changes the box's shape, or drops information, just by mapping with the identity function, it isn't really a functor.
2. **Mapping twice is the same as mapping once with the two functions glued together.** `box.fmap(f).fmap(g) == box.fmap(lambda a: g(f(a)))`. Doesn't matter whether `f` and `g` get applied separately in sequence, or composed first and applied once — same result either way.

These aren't just nice-to-haves — Ekans checks both laws for every `Functor` instance with Hypothesis, generating random values *and* random functions to try to break them, rather than trusting a couple of hand-picked examples.

## Const: the box that refuses to look

`Identity` is the functor that changes the *least*. `Const[A, B]` is the functor that changes *nothing at all*, and it earns that in a much stranger way: it doesn't have a value of type `B` to change in the first place.

```python
from ekans.const import Const
from ekans.functor import fmap

box = Const(value=1)
box.fmap(str)   # Const(value=1) -- f never ran
fmap(len, box)  # Const(value=1) -- same story
```

`Const[A, B]` holds a real, runtime value of type `A`. `B` exists purely at the type level — nothing of that type is ever stored, so `fmap` has no choice but to hand back the exact same held value, re-tagged from `Const[A, B]` to `Const[A, C]`, no matter what function you pass it or what that function does. In Haskell, this is `data Const a b = Const a`, with `instance Functor (Const a) where fmap _ (Const v) = Const v` — the underscore there is doing all the talking.

This is the same shape as `Proxy[A]` below in one sense (a phantom type parameter nothing ever touches) but a genuinely different animal in another: `Proxy` has *no* runtime field at all, while `Const` holds a completely real value — it just happens to be a value of the type that `fmap` isn't allowed to see.

**Why bother?** Because `Const` is the type that actually exercises `Functor` over a second parameter, rather than the whole container. It's a small, slightly odd example now, but this exact "hold a value, ignore the mapped-over type" trick is precisely what makes lens-like getters possible in richer profunctor-based libraries later on — a preview worth having early, even in its plainest form.

**Equality here works on *both* type parameters**, not just the one `fmap` touches — `Const[int, str]` and `Const[bool, str]` don't type-check as comparable (the held type differs), and neither do `Const[int, str]` and `Const[int, float]` (the phantom type differs, even though nothing of that type is ever actually stored):

```python
a: Const[int, str] = Const(value=1)
b: Const[int, float] = Const(value=1)

a == b
# error: Unsupported operand types for == ("Const[int, str]" and "Const[int, float]")  [operator]
```

Same mechanism as `Identity`'s type-safe equality above, just extended to two type parameters instead of one — mypy's invariance check works purely at the type level, so it catches the mismatch on `B` even though `B` never shows up in a runtime attribute to compare.

**Note for later:** `Const` still doesn't get a `Pointed` instance — `Monoid` now exists (see that section below), so the blocker's gone, but retrofitting `Const` is its own follow-up round rather than bundled in here. In Haskell, `Const`'s `Applicative` instance requires `Monoid a` (`pure _ = Const mempty`) — constructing a `Const[A, B]` from just a `B` needs *some* value of type `A` to hold, and the Monoid identity element is the only principled source.

**Conditionally a `Semigroup`, same story as `Identity`.** `Const[A, B]`'s held value is exactly what `mappend` would combine, so — same as `Identity` above — `Const` can `mappend` two of itself precisely when `A` can, phantom `B` along for the ride untouched. And same reasoning: since that constraint lives on `A`, `Const` never nominally inherits `Semigroup` either. It shows up purely via the free function, sharing the very same `ekans.semigroup.mappend` that handles `Identity` — the two live together as a single `@overload` set, since `mappend` has no generic `Apply[A]`-style fallback to fall back on. See the `Semigroup` section below for a real, runnable example.

`Const.mempty(SomeMonoidType)` holds the identity element the same way `Identity.mempty` wraps it — `Const.mempty(Box)` gives `Const(value=Box.mempty())`, `B` freely inferred from context, the same way `fmap` freely re-tags it.

`Const` is also `Extractable[A]` (see that section below) — `Const(value=5).extract()` returns `5`, the held `A`, never the phantom `B`. Worth noting alongside `Const[A, B]`'s two-type-parameter equality above: `Extractable[A]` and `Functor[B]` sit on *different* type parameters of the same class, and that composes cleanly — no conflict between the two.

## Pointed: getting a value into a box

Every box we've built so far, you build by calling its own constructor: `Identity(value=42)`, `Const(value=1)`. `Pointed` is what happens when you want to say that in a *generic* way — "give me a box of this shape, holding this value" — without hardcoding which shape.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

from ekans.pointed import Pointed

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class Box(Pointed[A], Generic[A]):
    value: A

    @classmethod
    def point(cls, value: A) -> "Box[A]":
        return Box(value=value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


Box.point(42)  # Box(value=42)
```

`Box` here is an illustrative stand-in, the same way it was in the `Functor` section above; `Identity` (see its section above) is the real, shipped example, and its `point` is exactly this shape.

`point` is a **classmethod**, not an instance method like `fmap`. That's not a style choice — there's no instance to call it on yet, that's the whole point (no pun intended, mostly). Compare: `fmap` transforms a box you already have; `point` conjures a box out of nothing but a bare value and a type.

That difference has a real consequence: `fmap` also gets a free function (`fmap(f, box)`) because the box being passed in already *knows* its own type parameter — mypy reads that straight off the value. `point` doesn't get that luxury. A free `point(Box, 42)` would only ever have a bare class reference to work with, and — checked this directly — it silently type-checks as `Box[Any]` rather than `Box[int]`, no error, just quietly losing the precision that makes any of this worth doing in the first place. `Box.point(42)` has no such problem: it's exactly as precise as `Box(value=42)`. So `point` stays classmethod-only — one honest way to spell it, instead of two, one of which lies to you a little.

In Haskell this is `pure` (or `return`, historically) — the thing that lifts a plain value into `f a` for whatever `Applicative`/`Monad` `f` you're working in. `Pointed` on its own doesn't do much more than that lift; it earns its keep once it's combined with `Apply` into `Applicative` later, the same way `Pointed` + `Apply` gives you `pure` *and* `<*>` together in Haskell.

## Reader: a box that's actually a function

Every box so far holds something you could point at: an int, a string, a value sitting there waiting. `Reader[R, A]` holds something stranger: a function, `R -> A` — "give me an environment, I'll give you a result." Think dependency injection, minus the framework: a `Reader[Config, int]` is a computation that hasn't run yet, waiting on a `Config` to actually produce its `int`.

```python
from ekans.reader import Reader

get_length: Reader[str, int] = Reader(run=len)
get_length.run("hello")  # 5
```

`fmap` works exactly like everywhere else — transform what comes out, leave the box's shape alone — except here "what comes out" is the function's eventual result, not something already sitting in the box:

```python
from ekans.functor import fmap

louder: Reader[str, str] = get_length.fmap(lambda n: f"{n} characters!")
louder.run("hello")  # '5 characters!'

fmap(lambda n: f"{n} characters!", get_length).run("hello")  # same thing
```

Under the hood, `fmap(f, reader)` is just function composition: it builds a *new* `Reader` whose `run` is `f` glued onto the end of the old `run`. Nothing gets called until you actually call `.run(env)` — `Reader` is lazy in exactly the sense that a function you haven't called yet is lazy.

**The equality wrinkle, explained as real theory, not an apology.** Every other box in this guide gets `==`: `Identity(value=1) == Identity(value=1)` is `True`. `Reader` doesn't, on purpose. Two Python functions that compute the same thing are never `==` to each other — Python compares functions by identity, not by behavior, and there's no way around that from inside the language. Giving `Reader` a `__eq__` that compares its wrapped function directly would be worse than useless: `reader.fmap(f)` builds a brand-new closure every time, so it would never equal anything, ever, without ever *looking* broken — no error, just an equality operator that silently always says no. The honest move is to not pretend: `Reader` just doesn't support `==` in any meaningful sense. If you need to know whether two `Reader`s behave the same, the real question is "do they produce the same result for the same environment?" — which means calling `.run(env)` on both and comparing outputs, for whichever environments you actually care about. That's *extensional* equality (functions are equal if they agree everywhere), and it's the same idea Ekans' own test suite leans on to verify `Reader`'s Functor laws, since `==` isn't available to check them the usual way.

`Reader` also implements `Pointed`: `Reader.point(5)` builds a `Reader` that ignores whatever environment it's given and always produces `5` — a computation that doesn't actually need the environment at all:

```python
always_five: Reader[str, int] = Reader.point(5)
always_five.run("this string is ignored entirely")  # 5
always_five.run("so is this one")  # 5

Reader.point(5).fmap(str).run("still ignored")  # '5'
```

Under the hood, `point` is built from a small standalone combinator, `const`: Haskell's `const :: a -> b -> a`, a function that ignores its second argument and always returns its first. `const(5)` is a function equivalent to `lambda _: 5`; `Reader.point(value) = Reader(run=const(value))`. It's not exported as part of `Reader`'s own concept — it's a small, general-purpose piece of plumbing that happens to live in `ekans.reader` because that's its only user so far.

One last bit of ergonomics: `Reader` is directly callable, so `reader(env)` works exactly like `reader.run(env)`:

```python
get_length("hello")  # 5 -- same as get_length.run("hello")
```

That's the whole bridge back to plain Python: anywhere a `Callable[[R], A]` is expected — `map()`, composing with an ordinary function, whatever — a `Reader` can just be handed over directly, no `.run` required.

`Reader` also implements `Apply` (see that section below): `.ap` threads the *same* environment into both the wrapped value and the wrapped function, not two independently-supplied ones —

```python
add_r: Reader[int, int] = Reader(run=lambda r: r)
multiply_by_r: Reader[int, Callable[[int], int]] = Reader(run=lambda r: (lambda x: x * r))

threaded = add_r.ap(multiply_by_r)
threaded.run(3)  # 9  -- both sides saw r=3, not two different r's
threaded.run(4)  # 16
```

If the environment leaking into both sides sounds obvious, it's worth checking: it would be just as easy to write an `ap` that accidentally used two *different* environments (say, by hardcoding one side), and the result would still type-check fine — the bug would only show up as wrong numbers at runtime. That's exactly why this got a behavioral test, not just a type-checked one.

Since `Reader` has both `point` and `ap`, it's an `Applicative` too (see that section below) — nothing extra to write, same as `Identity`.

**Conditionally a `Semigroup`, pointwise this time.** Same story as `Identity` and `Const` above — `Reader[R, A]` can `mappend` two of itself precisely when `A` can, and never nominally inherits `Semigroup` for the same reason. The combination happens *pointwise*: run both sides against the same environment, then `mappend` the two results — `mappend(f, g).run(r) == f.run(r).mappend(g.run(r))`. It shares the same three-way `ekans.semigroup.mappend` overload as `Identity`/`Const`. See the `Semigroup` section below for a real, runnable example.

`Reader.mempty(SomeMonoidType)` builds the identity element the same way `Reader.point` builds any other value — ignoring the environment entirely: `Reader.mempty(Box).run(anything)` always returns `Box.mempty()`, no matter what `anything` is.

`Reader` is also `Bind` (see that section below): `x.bind(f)` threads the *same* environment into both `self` and whatever `Reader` `f` produces, same threading story as `ap` — `x.bind(f).run(r)` calls `x.run(r)` first, feeds that result to `f`, then runs the resulting `Reader` against that same `r` again.

With both `Applicative` and `Bind` in hand, `Reader` is a `Monad` too (see that section below), the same free composition `Identity` gets — `class Reader(Monad[A], Generic[R, A])` is the whole story, no new methods needed.

## Apply: when the function is also in a box

`fmap` covers a lot of ground, but it has one blind spot: the function you're mapping with always has to be a plain, ordinary function sitting outside any box. What happens when the function itself is *also* stuck inside a box? That's `Apply`.

```python
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.apply import Apply, ap

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Box(Apply[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "Box[B]":
        return Box(value=f(self.value))

    def ap(self, f: "Box[Callable[[A], B]]") -> "Box[B]":
        return Box(value=f.value(self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


number: Box[int] = Box(value=5)
wrapped_str: Box[Callable[[int], str]] = Box(value=str)

number.ap(wrapped_str)   # Box(value='5')
ap(wrapped_str, number)  # Box(value='5') -- same thing, free-function form
```

Same convention as `fmap`: both the method and the free function put "the thing doing the transforming" first — `x.ap(f)` and `ap(f, x)`, matching `x.fmap(f)` and `fmap(f, x)`. `Box` here is a stand-in for illustration; `Identity` and `Reader` (see their sections above) are the real, shipped examples — `Reader`'s is the more interesting one, since its `ap` has to actually thread an environment through both sides rather than just unwrapping two boxes.

**The law, and its honest limit.** `Apply` has exactly one law of its own, before `Applicative` adds more: applying wrapped functions one at a time, left to right, gives the same answer as composing them first and applying once —

```
w.ap(v.ap(u.fmap(compose))) == w.ap(v).ap(u)
```

— where `compose(g)` builds the function `f -> (a -> g(f(a)))`. It's `Functor`'s composition law, generalized to functions that are themselves wrapped.

Worth knowing plainly: this law alone doesn't catch *every* bug. An `ap` that quietly ignores the function it's given and just hands back `self` unchanged satisfies this law perfectly — both sides collapse to the same "untouched" answer no matter what `u`, `v`, or `w` actually are. It took writing a genuinely wrong `ap` (one that double-applies the function) to actually see the law fail; the "ignore the argument" bug sailed straight through. That's not a flaw in the test — it's a real, inherent limit of associativity by itself, and it's exactly why `ap` still gets an ordinary example-based test (`box.ap(wrapped) == expected`) alongside the property test, not instead of it.

## Applicative: Pointed and Apply, together

`Applicative` doesn't add anything new — it's just the name for "has both `Pointed` and `Apply`." No new method, no new behavior. What it buys you is a guarantee: `point`, `ap`, and `fmap` actually agree with each other, expressed as four laws.

```python
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.applicative import Applicative

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Box(Applicative[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "Box[B]":
        return Box(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "Box[A]":
        return Box(value=value)

    def ap(self, f: "Box[Callable[[A], B]]") -> "Box[B]":
        return Box(value=f.value(self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


Box.point(5).ap(Box.point(str))  # Box(value='5')
```

Notice the class declaration: just `Applicative[A]`, nothing else — no separate `Pointed[A]`/`Apply[A]`/`Functor[A]` in the bases. That's on purpose, not a simplification: since `Applicative` already inherits both, listing them again creates a genuinely broken class (Python can't work out a consistent method resolution order, and raises a `TypeError` at class *definition* time, not at some later call). `Box` here is a stand-in for illustration; `Identity` (see its section above) is the real, shipped `Applicative` — and, being one, needed no new methods at all, just the same base-class change.

**The four laws.** These are what make `point`, `ap`, and `fmap` a single coherent system instead of three unrelated methods that happen to share a class:

1. **Identity** — applying a "do-nothing" wrapped function changes nothing: `v.ap(Box.point(lambda a: a)) == v`.
2. **Homomorphism** — wrapping a value and a function separately, then applying, is the same as applying first and wrapping the result: `Box.point(value).ap(Box.point(f)) == Box.point(f(value))`.
3. **Interchange** — it doesn't matter which side "starts wrapped": `Box.point(value).ap(u) == u.ap(Box.point(lambda fn: fn(value)))`.
4. **Composition** — the same associativity law `Apply` already has on its own (see that section above), restated using `point` for the wrapped composition operator instead of assuming it: `w.ap(v.ap(u.fmap(compose))) == w.ap(v).ap(u)`.

That last one is worth being honest about: it's the identical formula to `Apply`'s own associativity law — testing it again here isn't finding new bugs so much as confirming `point` doesn't quietly break something `ap` alone already got right.

**`liftA2`: running a two-argument function across two boxes at once.** `fmap` handles one-argument functions; `ap` lets you chain further arguments in one at a time. `liftA2` is the shortcut for the common two-argument case, built purely from `fmap`/`ap` that `Applicative` already provides:

```python
from ekans.applicative import liftA2
from ekans.identity import Identity

liftA2(lambda a, b: a + b, Identity(value=2), Identity(value=3))  # Identity(value=5)
```

Like `ap`, this needs its own `@overload` per concrete type to stay precise — a version typed only against the abstract `Applicative[A]`/`Applicative[B]` type-checks fine but silently hands back the loose `Applicative[C]` for every call, even a plain `Identity` one. That's worth knowing about generally: a free function that touches concrete types only through an abstract handle can look perfectly type-safe while quietly losing precision, with no error to catch it — the exact trap `Pointed.point`'s free-function form fell into and got rejected for entirely (see `Pointed` above). `liftA2` had a way out `point` didn't (a real generic implementation, so the overloads could be added rather than dropping the free function altogether), but the underlying lesson is the same.

## Semigroup: squishing two into one

Every type class so far has been about boxes: things that hold a value and know how to be mapped over, pointed into, or applied through. `Semigroup` is different — it's not about boxes at all. It's a property a plain type can have: knowing how to combine two of itself into a third.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

from ekans.semigroup import Semigroup

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class Box(Semigroup, Generic[A]):
    value: A

    def mappend(self, other: "Box[A]") -> "Box[A]":
        return Box(value=self.value + other.value)  # type: ignore[operator]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


Box(value=1).mappend(Box(value=2))  # Box(value=3)
```

`mappend` is Haskell's historical name for `<>` — from back when `Semigroup` hadn't yet been split out of `Monoid`. Ekans keeps the historical name rather than inventing a friendlier one, matching the project's general lean toward Haskell-faithful naming (`fmap`, `ap`, `point`) over what merely reads nicest in isolation.

**The one law.** `mappend` must be associative — grouping doesn't matter, only order does:

```
a.mappend(b).mappend(c) == a.mappend(b.mappend(c))
```

Addition satisfies this (`(1 + 2) + 3 == 1 + (2 + 3)`); subtraction doesn't (`(1 - 2) - 3 != 1 - (2 - 3)`) — which is exactly the kind of broken instance the law is there to catch.

**A first: no override boilerplate at all.** Every other type class here has needed its concrete overrides to narrow a return type away from something loose (`Functor[B]`, `Apply[B]`, ...), usually paired with a `# type: ignore[override]` explaining why. `Semigroup.mappend` sidesteps this entirely with `typing.Self`: the abstract method is declared `def mappend(self, other: Self) -> Self`, and `Self` already means "exactly whatever concrete class this is," precisely, for every subclass, with zero extra typing work.

**Why there's no `Identity`/`Const`/`Reader` class instance here.** Unlike `Functor` or `Apply`, `Semigroup` isn't unconditionally true of a container just because it holds *something* — `Identity[A]` only knows how to `mappend` when `A` itself does (there's no way to combine two `Identity[str]`s by squishing their `str`s together with a method `str` doesn't have). Haskell expresses this as a *constrained instance* (`instance Semigroup a => Semigroup (Identity a)`); Python has no direct equivalent at the class level. Ekans' answer: `Identity`, `Const`, and `Reader` never nominally inherit `Semigroup` at all. Instead, all three show up purely as `ekans.semigroup.mappend`, a single overloaded free function bounded by a `TypeVar("S", bound=Semigroup)`:

```python
from ekans.const import Const
from ekans.identity import Identity
from ekans.reader import Reader
from ekans.semigroup import mappend

mappend(Identity(value=Box(1)), Identity(value=Box(2)))  # Identity(value=Box(value=3))
mappend(Const(value=Box(1)), Const(value=Box(2)))        # Const(value=Box(value=3))

f: Reader[str, Box] = Reader(run=lambda env: Box(1))
g: Reader[str, Box] = Reader(run=lambda env: Box(2))
mappend(f, g).run("anything")  # Box(value=3) -- both sides ran against the same environment

mappend(Identity(value="a"), Identity(value="b"))
# error: Value of type variable "S" of "mappend" cannot be "str"  [type-var]
```

That rejection is real, not just documented convention — `str` genuinely isn't a `Semigroup`, and mypy catches it at the call site. `Box` above isn't a temporary stand-in waiting for a real type to catch up (the way it was for `Functor`) — demonstrating a constrained instance means there will always be a need for a small type that genuinely implements `Semigroup` on its own.

## Sum: addition, boxed

Every `Semigroup` example so far has been a stand-in built purely to demonstrate the shape of the law. `Sum[A]` is the first one that's actually useful: it wraps a value, and `mappend` is just `+`.

```python
from ekans.sum import Sum

Sum(value=1).mappend(Sum(value=2))  # Sum(value=3)
Sum(value=1.5).mappend(Sum(value=2.5))  # Sum(value=4.0)
```

Why bother wrapping a number just to add it? Because plain numbers don't come with one canonical `mappend` — there's more than one reasonable way to combine two of them (`Sum` picks `+`; `Product`, coming next, picks `*`), so `int`/`float` can't just *be* a `Semigroup` on their own without picking a side. Wrapping the number in `Sum` says *which* combining operation you mean, unambiguously. That's the whole reason Haskell's `Data.Monoid` bothers with a newtype here instead of giving `Int` a single built-in instance.

`Sum` is generic over anything that supports `+`, not just built-in numbers:

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

from ekans.sum import Sum

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class Vector(Generic[A]):
    x: A
    y: A

    def __add__(self, other: "Vector[A]") -> "Vector[A]":
        return Vector(x=self.x + other.x, y=self.y + other.y)  # type: ignore[operator]


Sum(value=Vector(x=1, y=2)).mappend(Sum(value=Vector(x=3, y=4)))
# Sum(value=Vector(x=4, y=6))
```

That's enforced structurally, not by inheritance: `Sum[A]` bounds `A` with a small `Protocol` requiring a self-typed `__add__`, so *any* type with an `__add__` that takes and returns its own type works — no need to explicitly subclass anything. Try it with a type that has no `__add__` at all and mypy rejects the `Sum(value=...)` call outright, before you ever get to `mappend`.

`Sum` is also `Extractable` (see that section below): `Sum(value=6).extract()` returns the plain `6` back out, no `Sum` wrapper left — the shape that makes `sum = lambda foldable: foldMap(Sum, foldable).extract()` work, once `foldMap` exists.

`Sum.mempty(int)` gives `Sum(value=0)`, `Sum.mempty(float)` gives `Sum(value=0.0)` — the additive identity, explicitly typed (see the `Monoid` section below for why it needs that explicit argument, and why `Sum` still isn't nominally a `Monoid`). Any custom type works too, as long as it implements a `.zero()` classmethod alongside its `__add__` — `int`/`float` are special-cased inside `mempty` since neither has one of its own.

## Product: multiplication, boxed

`Product[M]` is `Sum`'s sibling: same shape, different operation. `mappend` is `*` instead of `+`, bounded by its own small `SupportsMul` `Protocol` requiring a self-typed `__mul__`, structurally rather than by inheritance — same reasoning as `Sum`'s `SupportsAdd` above.

```python
from ekans.product import Product

Product(value=2).mappend(Product(value=3))    # Product(value=6)
Product(value=1.5).mappend(Product(value=2))  # Product(value=3.0)
```

Wrapping the number in `Product` rather than `Sum` says which combining operation you mean for the exact same underlying `int`/`float` — the same disambiguation `Sum` needed above, just picking the other one.

`Product` is also `Extractable`: `Product(value=6).extract()` returns `6`, same shape as `Sum`.

`Product.mempty(int)` gives `Product(value=1)`, `Product.mempty(float)` gives `Product(value=1.0)` — the multiplicative identity, same explicit-`Type[X]` shape as `Sum.mempty` and for the same reason (see the `Monoid` section below). Custom types need a `.one()` classmethod alongside `__mul__`.

## All: everyone has to agree

`Sum`/`Product` are generic over anything with the right operator. `All` isn't generic at all — it wraps exactly one `bool`, and `mappend` is logical AND:

```python
from ekans.all import All

All(value=True).mappend(All(value=True))    # All(value=True)
All(value=True).mappend(All(value=False))   # All(value=False)
```

The name gives away the intuition: combine a bunch of `All`s together and the result is `True` only if *all* of them were. Since there's nothing to be generic over — `bool` is `bool`, there's no version of AND that varies by what's inside — `All` skips the `Protocol`/`TypeVar` machinery `Sum`/`Product` needed entirely, and its `__eq__` is typed against plain `object` rather than needing the type-parameter-narrowing trick from `Identity`/`Sum`/`Product`, since there's no type parameter to mismatch in the first place.

`All` is also `Extractable[bool]` — not a generic `Extractable[A]`, since `All` itself was never generic: `All(value=True).extract()` returns `True`.

`All` is also, genuinely, a `Monoid` — the one type in this round with no erasure wall to hit, since it isn't generic over anything. `All.mempty()` is exactly the nullary classmethod `Monoid` promises, no `Type[X]` argument needed: `All.mempty() == All(value=True)`, `True` being AND's identity (combine anything with `True` and you get that thing back).

## Ap: a box, held by a box

`Sum`/`Product`/`All` combine plain values. `Ap[S]` combines *boxed* ones — it wraps an `Identity[S]` (where `S` is itself a `Semigroup`), and `mappend` reaches inside both boxes, combines what's there, and re-wraps the result:

```python
from dataclasses import dataclass

from ekans.ap import Ap
from ekans.identity import Identity
from ekans.semigroup import Semigroup


@dataclass(frozen=True, eq=False)
class Box(Semigroup):
    value: int

    def mappend(self, other: "Box") -> "Box":
        return Box(value=self.value + other.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


a = Ap(value=Identity(value=Box(value=1)))
b = Ap(value=Identity(value=Box(value=2)))
a.mappend(b)  # Ap(value=Identity(value=Box(value=3)))
```

Under the hood, `mappend` is `Ap(value=liftA2(lambda a, b: a.mappend(b), self.value, other.value))` — a direct transcription of Haskell's `mappend (Ap x) (Ap y) = Ap (liftA2 mappend x y)`, which is exactly why `liftA2` (above) needed to exist first: `Ap` isn't reimplementing that logic by hand, it's built straight on top.

**The honest gap:** Haskell's `Ap` is `newtype Ap f a = Ap { getAp :: f a }`, generic over *any* `Applicative f` — you could build `Ap Maybe Int`, `Ap [] Int`, `Ap IO Int`, whatever. Ekans' `Ap[S]` can't do that: it's fixed to wrap `Identity[S]` specifically, not generic over the box itself. This isn't a shortcut taken for convenience — it's a real wall. Python's type system has no *higher-kinded types*: a `TypeVar` can only ever stand for a concrete type, never for a type constructor waiting to be filled in. Try to write `Generic[F, A]` with a field typed `F[A]` where `F` is a bare `TypeVar`, and mypy refuses outright (`Type variable "F" used with arguments`) — there's no way to say "some box, whichever one, applied to `A`" the way Haskell's kind system lets you. So Ekans' `Ap` picks one box (`Identity`, the simplest one available) and stops there, rather than pretending to a generality the type system genuinely can't check.

`Ap` is also `Extractable[S]` — and, unlike every other instance in this round, it doesn't stop at its own immediate field. `Ap[S]`'s `.value` is an `Identity[S]`, but `extract` reaches straight through it to `S`: `a.extract()` on `Ap(value=Identity(value=Box(value=1)))` returns `Box(value=1)` directly, not `Identity(value=Box(value=1)))`. The implementation is exactly that one-line delegation, `self.value.extract()` — `Identity` being `Extractable` too is what makes it possible.

`Ap.mempty(SomeMonoidType)` is the simplest `mempty` in the package — no `int`/`float` registry needed the way `Sum`/`Product` need one, since `S` is already bound to `Semigroup` and the `Type[X]` argument is bound one notch tighter, to `Monoid`, which already has its own real `mempty()`. `Ap.mempty` just delegates straight to it: `Identity(value=value_type.mempty())`.

## Extractable: getting a value out of a box

`Pointed` (above) is "give me a box of this shape, holding this value" — a value goes in, a box comes out. `Extractable` runs that exact arrow backwards: a box goes in, its value comes out.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

from ekans.extractable import Extractable

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class Box(Extractable[A], Generic[A]):
    value: A

    def extract(self) -> A:
        return self.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


Box(value=42).extract()  # 42
```

`Box` here is an illustrative stand-in, the same way it was for `Functor`/`Pointed` above; `Identity`, `Sum`, `Product`, `All`, `Const`, and `Ap` are the real, shipped examples — every type in the package that genuinely holds exactly one value now has `extract` (`Reader`/`Star` don't, since they wrap a function rather than holding a value directly, and `Proxy` doesn't, since it holds nothing at runtime at all).

Like `point`, `extract` needed no design detour to get precise: it's an ordinary instance method narrowing only its *return* type per concrete class, which mypy already tracks exactly — no `# type: ignore` anywhere, on any of the six instances.

**A law that shows up when a type is both.** `Extractable` on its own has no law to check — same as `Pointed` on its own. But a type that implements *both* has a real, checkable property connecting them: build a box from a value with `point`, then immediately `extract` it back out, and you get the original value — `extract(point(a)) == a`. `Identity` is currently the only type in the package that's both `Pointed` and `Extractable` (`Sum`/`Product`/`All`/`Const`/`Ap` are `Extractable` but were never `Pointed` to begin with), so this is checked directly against `Identity` rather than through a generic reusable helper — the same "wait for a second real instance before generalizing" rule this project already applies to `@overload` growth.

`Pointed`/`Extractable` are also the first deliberate step toward `Comonad` (a `Functor` that can `extract` and `extend`) — the mirror image of how `Monad` got built up here from `Pointed`/`Functor`/`Apply`/`Bind` piece by piece, just run in the opposite direction. `Comonad` itself, and the `extend`/`duplicate` half of it, aren't built yet — see "Coming soon" below.

`extract` connects to more than just `point`, too — `extract(w.fmap(f)) == f(w.extract())` and `x.ap(f).extract() == f.extract()(x.extract())` both hold for `Identity`, and `mappend(x, y).extract() == x.extract().mappend(y.extract())` holds everywhere a type is both `Semigroup` and `Extractable`. See `docs/specs/invariance-audit.md` for the full cross-class inventory, including the pairs that were checked and genuinely don't have a law (like `Const`'s `Functor`/`Extractable` naturality — `fmap` and `extract` touch different type parameters there, so the law isn't just false, it isn't even well-typed).

## Monoid: something out of nothing

`Semigroup` tells you how to combine two of something. `Monoid` adds the other half: a value that does *nothing* when combined — combine anything with it, on either side, and you get the original thing back unchanged.

```python
from dataclasses import dataclass

from ekans.monoid import Monoid

@dataclass(frozen=True, eq=False)
class Box(Monoid):
    value: int

    def mappend(self, other: "Box") -> "Box":
        return Box(value=self.value + other.value)

    @classmethod
    def mempty(cls) -> "Box":
        return Box(value=0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


Box.mempty().mappend(Box(value=5))  # Box(value=5) -- unchanged
Box(value=5).mappend(Box.mempty())  # Box(value=5) -- unchanged either side
```

**The honest wall this hits.** Haskell's `mempty :: a` is nullary — no arguments, the type alone tells you what to build. Python can't do this for a *generic* container: types are erased at runtime, so a hypothetical `Sum.mempty()` has no way to know, when the code actually runs, whether you wanted `int`'s `0` or `float`'s `0.0`. This isn't a hunch — it was checked directly, and the result is worse than a type error: a hardcoded `Sum.mempty()` lets mypy *confidently and wrongly* infer `Sum[float]` from context while the running code silently hands back an `int` `0`. A silent wrong answer that type-checks clean is far worse than a loud one that doesn't.

So `Sum`/`Product`/`Ap`'s `mempty` takes the type explicitly — `Sum.mempty(int)`, not `Sum.mempty()` — trading a little of Haskell's elegance for something that's actually correct. And because a classmethod requiring that extra argument doesn't honestly satisfy `Monoid`'s zero-argument contract (verified: `mypy --strict` flags it as a real signature-incompatibility error, not a narrow-return-type situation `# type: ignore` could paper over), those three don't nominally inherit `Monoid` at all — only `All` does, since it isn't generic over anything and has nothing to erase. See each type's own section above for its `mempty`.

## Bind: chaining boxes without nesting them

`fmap` transforms what's inside a box with a plain function. `Apply` lets that function itself be boxed. `Bind` handles a third case: what if the function you want to apply *already produces a box of its own*? Plain `fmap` would leave you with a box of boxes — `Bind` flattens that back down to one.

```python
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.bind import Bind

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Box(Bind[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "Box[B]":
        return Box(value=f(self.value))

    def ap(self, f: "Box[Callable[[A], B]]") -> "Box[B]":
        return Box(value=f.value(self.value))

    def bind(self, f: Callable[[A], "Box[B]"]) -> "Box[B]":
        return f(self.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


Box(value=5).bind(lambda a: Box(value=str(a)))  # Box(value='5')

from ekans.bind import bind
bind(lambda a: Box(value=str(a)), Box(value=5))  # Box(value='5') -- free-function form
```

Compare that to `fmap`: `Box(value=5).fmap(lambda a: Box(value=str(a)))` would give you `Box(value=Box(value='5'))` — a box holding a box, since `fmap` has no idea the function it was handed already produces one. `bind` is exactly `fmap` plus automatically un-nesting the result. This is Haskell's `>>=`, spelled as a method (`x.bind(f)`) and a free function (`bind(f, x)`, action-first, matching this project's `fmap`/`ap` convention rather than `>>=`'s own value-first order).

**A real precision gap, worth knowing about.** Pass the free function a bare, unannotated lambda the way the example above does, and — verified directly — mypy silently infers the whole call as `Any`, not even the loose `Bind[...]`. The free function's `f`-first argument order means mypy has to make sense of the lambda before it's resolved `x`'s type well enough to pick the right overload; without an explicit parameter type on the lambda, that inference just gives up quietly instead of erroring. The method form doesn't have this problem — `x.bind(lambda a: Box(value=str(a)))` infers precisely, since `self` already anchors the type before the lambda is ever looked at. When precision matters (not just runtime correctness), prefer the method form, or give the free function a properly-typed `def` instead of a bare lambda.

**The one law: associativity.** Chaining two binds one at a time gives the same answer as threading the second function through the first's result:

```
m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))
```

Verified directly: holds for a correct `bind`, and genuinely caught by a deliberately broken one (applying `f` twice).

**Why `Const` doesn't get a `Bind` instance.** `Const[A, B]`'s `bind` would need `f: Callable[[B], Const[A, C]]` — but `Const` never stores anything of type `B` to actually hand `f`, the exact same reason `Const.fmap` is a no-op re-tag. The only well-typed `bind` for `Const` would have to ignore `f` entirely, which isn't a stylistic choice to skip — it's two real problems, checked directly rather than assumed: it offers *zero* capability beyond what `fmap` already provides (a `bind` that never calls its function isn't doing anything new), and it has a genuine type-precision failure — `reveal_type` on a `Const.bind(...)` call resolves to `Const[int, Never]`, not a sensible type, because nothing in the expression ever pins down what the result's phantom type should be. `Identity` and `Reader` (see their sections above) are the real, shipped instances.

## Monad: Applicative and Bind, evolved

`Applicative` lets you lift plain values and apply wrapped functions. `Bind` lets you chain box-producing functions without nesting boxes. `Monad` is just both of those at once — no new capability, no new method, purely the combination:

```python
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from ekans.monad import Monad

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Box(Monad[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "Box[B]":
        return Box(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "Box[A]":
        return Box(value=value)

    def ap(self, f: "Box[Callable[[A], B]]") -> "Box[B]":
        return Box(value=f.value(self.value))

    def bind(self, f: Callable[[A], "Box[B]"]) -> "Box[B]":
        return f(self.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)
```

Any type implementing all four methods above (`fmap`, `point`, `ap`, `bind`) is automatically a `Monad` just by declaring `Box(Monad[A], Generic[A])` instead of listing `Applicative`/`Bind` separately — same trick `Applicative` already used for `Pointed`+`Apply`.

**Two new laws, both about `point` meeting `bind`.** `Bind`'s own associativity law doesn't change here — it's already proven for anything that's `Bind`, which `Monad` requires anyway, so it isn't retested. What's genuinely new is the pair of laws connecting the two halves: building a box with `point` and immediately unwrapping it with `bind` should be the same as just calling the function directly, and binding a box with `point` itself should change nothing:

```
point(a).bind(f) == f(a)   # left identity
m.bind(point) == m         # right identity
```

Verified directly: both hold for a correct implementation, and left identity genuinely catches a broken `point` (one that quietly nudges its argument) — not a vacuous pass.

## Coming soon

These don't exist in the package yet. Each one gets its own full section, complete with theory and jokes, the moment it lands — this is just so you can see where the hierarchy is headed.

- **Extend** — the dual of `Bind`: instead of chaining box-producing functions together, it lets a function that consumes a *whole box* (`w a -> b`) be applied across a structure without collapsing it (`extend`/`duplicate`).
- **Comonad** — `Functor`, `Extractable`, and `Extend`, together — the mirror image of `Monad`.
- **Category** — the algebra of "and then" (composition), plus a no-op that does nothing when composed.
- **Profunctor** — a box with an in-door and an out-door, each independently adaptable.
- **Strong** — a `Profunctor` that can politely ignore half a tuple while it works on the other half.
- **Star** — a `Profunctor` built by wrapping up a function that returns a *boxed* value (`a -> f b`) instead of a plain one, so `dimap` can reach in through the box too. This is the interesting one: when the box is a `Monad`, composing two `Star`s is exactly Kleisli composition — chaining effectful functions end to end. Give `Star` its own `Category` instance on top of that composition and you get Haskell's `Kleisli` arrow — the `Arrow` built for monadic effects. (Not every `Arrow` looks like this — plain functions are an `Arrow` too, no box in sight — but the Kleisli case, the one people actually reach for, is precisely `Star` plus `Category`.) It comes essentially free once `Category`, `Strong`, and `Monad` already exist, rather than needing its own bespoke machinery.
- **Proxy[A]** — a box that was never holding anything to begin with; `A` exists only on the label, never at runtime. Named after Haskell's `Data.Proxy` — not to be confused with the `profunctors` package's *different* `Forget` type, which actually does hold a value and might show up here later under its own name. `Const` above is its cousin with a real value inside.
