# TurboKnight 5 — v56

An improved version of the supplied Scratch chess engine by destructor_chess / ababoin07.

**Open [TurboKnight-5-v56.sb3](TurboKnight-5-v56.sb3) in Scratch or TurboWarp.** All original artwork, sounds, embedded network weights and opening-book data are preserved. The uploaded v52 and the earlier v53 are retained in `baseline/` for reproducible comparisons.

## v56: original pseudo-legal generation restored

v55 became slow because it regenerated full enemy reply lists to validate kings and quiescence moves. Those probes are removed. Normal search again follows **generate pseudo-legal moves → make → search the child → undo**, with illegal predecessors rejected by the child.

- The original precomputed ray/knight/pawn **king-target capture lookup** is reused and its check result cached. It does not generate an enemy move list or execute a virtual king capture. This is the same small geometric lookup used in the initial project; it is not a claim that check detection has no work.
- Quiet quiescence uses capture/promotion generation. Stand-pat cutoffs happen before generating a list; checked positions get full pseudo-legal evasions.
- Stalemate validation usually uses a cheap legal pawn/knight/king witness. A full-list fallback is reserved for unusual immobilized positions. An unaligned non-king source in a non-check position cannot expose its king, so that witness needs no make/unmake.
- King-capture and promotion flags are set as captures/promotions are appended. Ordinary generations no longer have an extra scan over every move; promotion expansion runs only when a promotion exists.
- No recursive search node generates a separate full enemy reply list. Regression tests enforce zero generations for a quiet stand-pat cutoff and at most one generation per searched node.
- The scalar, preallocated context stack and the v55 broadcast/GUI fixes remain intact.

The **compiled TurboWarp** and **real-GUI** comparisons against the original uploaded v52 and v55 are in [the v56 performance report](benchmarks/V56.md). Raw node counts and distinct-position counts are both recorded: v52 counts a depth-zero NEG-to-Q delegation twice, whereas v56 counts that position once. Search trees differ, so nominal-depth timings are also reported and must not be confused with position throughput.

## GUI regression coverage

v54's invalid broadcast-menu encoding is still fixed. The browser regression reproduces that old failure as a negative control, then tests v56 with real rendering, broadcasts and the TurboWarp compiler: enter thinking time, play `e2–e4`, receive a reply, play `g1–f3` with the book disabled, receive another reply, and restart for a new game. Engine and controller boards must stay synchronized.

## Search and context implementation

- Every node-local search value is a **scalar variable**. Each negamax, quiescence and perft call saves and restores the complete 26-field live caller context in **132 preallocated stack frames**. Normal completion, re-search, cutoff, terminal-position and timeout exits all pass through the return wrapper. Scratch already retains repeat bounds in its loop frames; overwritten-before-use scratch temporaries are not copied a second time.
- The old per-depth score/check/move/reduction/extension/TT-enable lists are gone. Move buffers have 512 preallocated slots **per call frame**, independent of chess depth. A nested search at the same ply cannot overwrite its caller's moves. `search.result.*` carries child results without a depth-indexed return list.
- Per-depth killers are replaced by a shared, bounded **side/from/to history table**. TT moves, promotions and material-aware MVV/LVA precede quiet history moves.
- Correct principal-variation search: a reduced search that raises alpha is verified at full depth before a full-window re-search. The initial logarithmic reduction formula and pseudo-move ordinal are restored; checking moves and promotions retain explicit protections.
- Mate-distance bounds and normalized TT mate scores; standard bounded check extensions; widening aspiration windows from depth four.
- Reverse-futility uses the initial `120 + 30 * depth²` margin and quiet-predecessor guard, alongside quiescence delta pruning. Reverse futility waits for a legal move, excludes PV/check/endgame/mate nodes, and does not store its shortcut in the TT. Delta pruning protects checks, promotions and low-material endings.
- Quiescence detects stalemate before accepting stand-pat, searches quiet check evasions and all promotions, and handles repetition/fifty-move claims. Checkmate takes precedence over a draw claim.
- A node budget and tighter time checks unwind safely. The driver keeps the last **completed** iteration and a verified legal fallback if no iteration completes. It no longer relies on an arbitrary TT entry to choose the final move.
- All four promotions are generated, made, undone and represented correctly in UCI, the DCI controller, PGN and engine/GUI synchronization. Human clicks without a suffix still default to queen. Promotion rehashing and en-passant pawn counting are corrected.
- Tapered evaluation clamps the interpolation phase in promoted positions. Stale, undeclared `engine.init` argument reporters are replaced with explicit configuration.

Board arrays, lookup tables, NNUE tensors, the transposition table and the existing **preallocated position undo/history stack** remain lists because they represent collections, not per-depth search locals. Position undo uses its move-stack pointer, not a search-depth offset. The only search node-state lists are the explicit context stack and frame-owned move buffers.

## NNUE decision (historical v54 comparison)

The embedded 769→96→32→1 network is available through an exact sparse first-layer refresh and the existing forward pass. Tests check the sparse accumulator against the dense original to `1e-9`.

**NNUE remains disabled by default.** In the recorded **v54** 0.5-second comparisons it searched far fewer nodes and solved 7/8 scored cases versus 8/8 for the default evaluator. Numeric agreement with the old network does not establish playing strength. No claim of NNUE or Elo improvement is made.

Build an experimental candidate with `python3 tools/build.py --nnue --output build/NNUE-candidate.sb3`, or change the Scratch variable `search.use_nnue` for experiments. The network weights have not been retrained.

## Build and test

Use the existing checkout; a separate Git worktree is unnecessary. Python 3.10+ and Node.js 20+ are required (validated with Python 3.12 and Node 24).

```sh
npm ci --ignore-scripts
npx playwright install --with-deps chromium
npm test
```

`npm test` rebuilds the project, checks the archive/block graph, executes the engine in Scratch VM, compares legal moves and perft with chess.js, validates incremental hashes/evaluation and make/unmake, checks all scalar fields on nested and early returns, and tests DCI promotions. The engine unit tests substitute assets only in their in-memory VM. The browser regression uses the real assets, renderer and compiler. Chromium may be selected with `CHROMIUM_PATH`; the test also recognizes `/usr/bin/chromium`.

The Python builder in `tools/` is the editable source for the new search. It reads the v53 baseline and writes the new Scratch blocks and a deterministic `.sb3` archive. `build/project.json` is available for inspection after a build. The runtime engine itself is Scratch blocks, not JavaScript injected into the application.

```sh
python3 tools/build.py
python3 tools/build.py --no-history --no-lmr --no-pruning --output build/Search-without-heuristics.sb3
python3 tools/build.py --nnue --output build/NNUE-candidate.sb3
node tests/benchmark.js TurboKnight-5-v56.sb3 time benchmarks/v56-time.json
node tests/benchmark.js TurboKnight-5-v56.sb3 depth benchmarks/v56-depth.json
```

See [benchmarks](benchmarks/README.md) for raw measurements and their limits. The comparisons demonstrate specific improvements and tradeoffs; they are not an Elo test or proof of superiority in arbitrary positions. The v56 GUI path and TurboWarp compiler are now tested through real browser input. The old strength comparisons describe v54; they are not new strength or speed claims for v56.
