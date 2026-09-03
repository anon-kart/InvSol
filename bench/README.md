# InvSol loop benchmark

Twenty-two Solidity contracts used to validate the InvSol pipeline. They were
written so that every loop pattern listed in Table I of the paper appears at
least once, alongside the access-control shapes the test harness needs and a
small number of deliberately seeded bugs.

## Layout

    contracts/       the Solidity sources
    manifest.json    expected loop patterns, categories and postconditions
    check_benchmark.py  compiles each contract and reports recovered loop facts
    ir/              generated, one IR JSON per contract

## Running

From the InvSol project root, with the virtual environment active:

    python bench/check_benchmark.py

Each line reports the number of functions, loops and accumulator facts found,
and flags any contract whose recovered loop categories disagree with the
manifest.

## Coverage

Loop patterns, using the names from Table I:

| Pattern | Contracts |
| --- | --- |
| Accumulator | 16 |
| Counter Logic | 14 |
| Mapping Update | 9 |
| Indexed Traversal | 8 |
| Proportional Split | 3 |
| External Calls | 3 |

Loop categories, using the names from Table VIII: simple, nested and dynamic.
Nesting reaches three levels in `TripleNest.sol`. Ten contracts carry access
modifiers, including `RoleRegistry.sol`, which has two distinct roles on
different functions.

Compiler pragmas are mixed on purpose: nineteen use a caret range, two pin an
exact version, and one uses an explicit range. This exercises per-file compiler
selection. All three forms are satisfied by solc 0.8.19.

## Seeded bugs

Three contracts contain deliberate faults, recorded under `seeded_bugs` in the
manifest.

`OffByOne.sol` has two loops whose index runs one step past the end of the
array, and a window calculation that underflows. `Escrow.sol` provides a safe
release that follows checks-effects-interactions and an unsafe one that makes a
raw call before clearing state. `GasBounded.sol` offers a batched traversal and
an unbounded one over the same queue.

Each faulty function is paired with a correct counterpart, so a tool can be
scored on whether it separates the two rather than merely flagging the file.
