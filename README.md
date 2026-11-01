# TurboKnight 5 — v55

An improved version of the supplied Scratch chess engine by destructor_chess / ababoin07.

**Open [TurboKnight-5-v55.sb3](TurboKnight-5-v55.sb3) in Scratch or TurboWarp.** All original artwork, sounds, embedded network weights and opening-book data are preserved. The v53 file from the preceding revision is retained in `baseline/` for comparisons.

## v55 repair

v54 computed a reply but sent its `dci message` broadcast as an executable menu reporter instead of a literal broadcast input. The controller therefore never received the move. Both generated broadcasts now use the correct Scratch representation and registered broadcast IDs. The previous unit harness muted broadcasts, so it did not expose this integration failure.

A real Chromium/TurboWarp regression now starts the unmodified graphical project, answers the thinking-time prompt, clicks `e2–e4`, verifies Black’s reply and both boards, plays `g1–f3` with the book disabled to force search, and restarts for another game. Broadcasts, rendering, input polling and the TurboWarp compiler remain active. The old v54 archive is retained only as a negative control that reproduces the stalled turn.

Legality now uses **king disappearance**: capture generation finds a pseudo-reply that can take the opponent’s king, makes that capture temporarily, checks the missing king, then undoes it. A normal search child reports its predecessor’s legality from its generated moves, rather than scanning square attacks after every move. A reserved probe frame handles node check status, quiescence terminal validation, and the starting, transit and final castling squares. The engine makes **zero calls** to `tools.is_square_attacked`; the legacy routine remains available to the independent test harness.

## Search and context implementation

- Every node-local search value is a **scalar variable**. Each negamax, quiescence and perft call saves and restores a complete 30-field context in **132 preallocated stack frames**. Normal completion, re-search, cutoff, terminal-position and timeout exits all pass through the return wrapper.
- The old per-depth score/check/move/reduction/extension/TT-enable lists are gone. Move buffers have 512 preallocated slots **per call frame**, independent of chess depth. A nested search at the same ply cannot overwrite its caller's moves. `search.result.*` carries child results without a depth-indexed return list.
- Per-depth killers are replaced by a shared, bounded **side/from/to history table**. TT moves, promotions and material-aware MVV/LVA precede quiet history moves.
- Correct principal-variation search: a reduced search that raises alpha is verified at full depth before a full-window re-search. Check evasions, checking moves and promotions are protected from late-move reductions; PV nodes are not reduced.
- Mate-distance bounds and normalized TT mate scores; standard bounded check extensions; widening aspiration windows from depth four.
- Conservative reverse-futility and quiescence delta pruning. Reverse futility waits for a legal move, excludes PV/check/endgame/mate nodes, and does not store its shortcut in the TT. Delta pruning protects checks, promotions and low-material endings.
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
node tests/benchmark.js TurboKnight-5-v55.sb3 time benchmarks/v55-time.json
node tests/benchmark.js TurboKnight-5-v55.sb3 depth benchmarks/v55-depth.json
```

See [benchmarks](benchmarks/README.md) for raw measurements and their limits. The comparisons demonstrate specific improvements and tradeoffs; they are not an Elo test or proof of superiority in arbitrary positions. The v55 GUI path and TurboWarp compiler are now tested through real browser input. The old strength comparisons describe v54; they are not new strength or speed claims for v55.
