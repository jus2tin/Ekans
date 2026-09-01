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

**Note for later:** `Const` doesn't get a `Pointed` instance yet, and won't until `Semigroup`/`Monoid` exist. In Haskell, `Const`'s `Applicative` instance requires `Monoid a` (`pure _ = Const mempty`) — constructing a `Const[A, B]` from just a `B` needs *some* value of type `A` to hold, and the Monoid identity element is the only principled source. No `Monoid`, no honest `Const.point`.

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

## Coming soon

These don't exist in the package yet. Each one gets its own full section, complete with theory and jokes, the moment it lands — this is just so you can see where the hierarchy is headed.

- **Apply** — what happens when the function you want to call is *also* stuck inside a box (`ap`).
- **Applicative** — `Pointed` and `Apply` shake hands and agree to work together.
- **Bind** — chaining box-producing functions together without ending up with a box of boxes (`>>=`).
- **Monad** — `Applicative` and `Bind`, evolved.
- **Semigroup** — anything you know how to squish two of together into one.
- **Monoid** — a `Semigroup` that also knows how to make something out of *nothing* (an identity element).
- **Category** — the algebra of "and then" (composition), plus a no-op that does nothing when composed.
- **Profunctor** — a box with an in-door and an out-door, each independently adaptable.
- **Strong** — a `Profunctor` that can politely ignore half a tuple while it works on the other half.
- **Star** — a `Profunctor` built by wrapping up a function that returns a *boxed* value (`a -> f b`) instead of a plain one, so `dimap` can reach in through the box too. This is the interesting one: when the box is a `Monad`, composing two `Star`s is exactly Kleisli composition — chaining effectful functions end to end. Give `Star` its own `Category` instance on top of that composition and you get Haskell's `Kleisli` arrow — the `Arrow` built for monadic effects. (Not every `Arrow` looks like this — plain functions are an `Arrow` too, no box in sight — but the Kleisli case, the one people actually reach for, is precisely `Star` plus `Category`.) It comes essentially free once `Category`, `Strong`, and `Monad` already exist, rather than needing its own bespoke machinery.
- **Proxy[A]** — a box that was never holding anything to begin with; `A` exists only on the label, never at runtime. Named after Haskell's `Data.Proxy` — not to be confused with the `profunctors` package's *different* `Forget` type, which actually does hold a value and might show up here later under its own name. `Const` above is its cousin with a real value inside.
