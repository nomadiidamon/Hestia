# Semantics

This document captures the behavioral guarantees that **both** the C++ and
Python implementations must uphold. If the two implementations ever disagree
on something described here, that's a bug in one of them — this file is the
tiebreaker.

> This is a placeholder. Replace the sections below with the actual
> behavioral contract of your project.

## Why This Document Exists

Having two independent implementations of the same thing is only useful if
they actually behave the same way for the same inputs. `concepts.md`
describes *what things are*; this document describes *how they must behave*,
so that:

- Contributors changing one implementation know what they must preserve.
- Contributors changing the other implementation have a spec to check
  against, instead of reverse-engineering behavior from the other language's
  source.
- Test suites in both `cpp/` and `python/` can be written against the same
  statements and are expected to assert the same outcomes.

## Guarantees

List the specific, checkable behaviors both implementations must match.
Prefer precise, testable statements over prose.

### Example format

- **Input validation:** _Given [condition], both implementations must
  [reject / accept / normalize] the input by [doing X]._
- **Error handling:** _Given [failure condition], both implementations must
  raise/return [specific error type or code], with [specific message or
  payload shape]._
- **Numeric behavior:** _Rounding, overflow, and precision rules that must
  match bit-for-bit or within a defined tolerance._
- **Ordering / determinism:** _Whether operations are guaranteed to be
  order-stable, deterministic, thread-safe, etc._
- **Serialization formats:** _Any on-disk or over-the-wire format produced or
  consumed by either implementation must be byte-for-bit / field-for-field
  compatible with the other._

## Explicitly Out of Scope

Things that are *allowed* to differ between implementations (e.g.
performance characteristics, internal error message wording, memory layout)
should be listed here so nobody files a "bug" against an intentional
difference.

## Testing This Contract

Describe (or link to) how cross-language conformance is actually tested —
e.g. a shared fixture/golden-file format under a common directory, consumed
by both `cpp/` and `python/` test suites, run via `.github/workflows/build.yml`.
