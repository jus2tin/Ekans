# The Ekans How-To

*A field guide to growing pure functional types in Python, one small abstract class at a time.*

This is a single article for now. As the library grows, the sections below are written to stand on their own — each one explains its concept without leaning on the sections after it — so that one day they can be lifted out into their own pages, wiki-style, without anyone having to rewrite a word. Until then: one file, scroll away.

Every concept, type, and function that exists in the package gets a section here. The ones that don't exist *yet* get a stub, so you can see the whole shape of where this is headed.

## Contents

- [Functional: the box with a broken lid](#functional-the-box-with-a-broken-lid)
- [Identity: the box that changes nothing](#identity-the-box-that-changes-nothing)
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

In Haskell this is `newtype Identity a = Identity a` — a type that exists almost entirely to prove a point. Once `Functor` lands in Ekans, `Identity` will be the textbook example of it: calling `box.map(str)` will turn `Identity(value=42)` into `Identity(value="42")` — same box, transformed insides, nothing else disturbed. That's the whole idea of a functor in one sentence: **change what's inside without changing the shape of the container.** `Identity` is the functor that changes the *least* — it's the control group.

Right now, before `Functor` exists, `Identity` is just that: a small, honest, immutable box. Think of it as a courier who picks up your package, carries it exactly as-is, and hands it back unopened. Not very exciting on its own — but every functor law anyone will ever write a Hypothesis test for gets checked against this box first, because if a law doesn't hold for the box that does nothing, it isn't going to hold for anything fancier either.

## Coming soon

These don't exist in the package yet. Each one gets its own full section, complete with theory and jokes, the moment it lands — this is just so you can see where the hierarchy is headed.

- **Pointed** — how a value gets *into* a box in the first place (`point`, a.k.a. `pure` in Haskell).
- **Functor** — the `map` you already know from lists, generalized to work on any box shape.
- **Apply** — what happens when the function you want to call is *also* stuck inside a box (`ap`).
- **Applicative** — `Pointed` and `Apply` shake hands and agree to work together.
- **Bind** — chaining box-producing functions together without ending up with a box of boxes (`>>=`).
- **Monad** — `Applicative` and `Bind`, evolved.
- **Semigroup** — anything you know how to squish two of together into one.
- **Monoid** — a `Semigroup` that also knows how to make something out of *nothing* (an identity element).
- **Category** — the algebra of "and then" (composition), plus a no-op that does nothing when composed.
- **Profunctor** — a box with an in-door and an out-door, each independently adaptable.
- **Strong** — a `Profunctor` that can politely ignore half a tuple while it works on the other half.
- **Star** — a `Profunctor` built by wrapping up a function that returns a *boxed* value (`a -> f b`) instead of a plain one, so `dimap` can reach in through the box too. This is the interesting one: when the box is a `Monad`, composing two `Star`s is exactly Kleisli composition — chaining effectful functions end to end. That makes `Star` a more powerful stand-in for Haskell's `Arrow`, and it comes essentially free once `Category`, `Strong`, and `Monad` already exist, rather than needing its own bespoke machinery.
- **Forget[A]** — a box that was never holding anything to begin with; `A` exists only on the label, never at runtime.
- **Const[A, B]** — `Forget`'s cousin: it *does* hold a real value of type `A`, and simply refuses to look at `B` at all.
