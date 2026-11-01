# Recorded comparisons

The JSON files are actual runs in Scratch VM 5.0.300 on Node 24/Linux. Every position starts with a cold TT and cleared history; the opening book is disabled. Variants run sequentially to avoid competing for CPU.

`tests/positions.js` contains 12 small positions: eight scored tactical/rule cases, and four diagnostic positions. The expected moves emphasize mates, winning captures, a rook underpromotion to avoid stalemate, promotion notation, and legal check evasions. This is a small regression suite, **not an independent strength/Elo benchmark**. An en-passant position is diagnostic only because capturing en passant need not be its best move.

## Half-second move budget

| Variant | Scored cases solved | Illegal moves | Total nodes |
| --- | ---: | ---: | ---: |
| Prior v53 | 6/8 | 1 | 16,040 |
| v54 default | 8/8 | 0 | 3,940 |
| v54 NNUE candidate | 7/8 | 0 | 758 |
| v54 without history/LMR/pruning | 8/8 | 0 | 3,629 |

See `*-time.json` for individual wall times, moves, depths and counts. Requested time is 0.5 seconds per position; reported wall time includes the driver's work. Mates terminate early in v54. v53 repeats some solved mates to its iteration limit, so its reported depth of 64 does not indicate a 64-ply search. At least one difficult position completes no iteration; v54 still returns its verified legal fallback.

Node counts are not directly comparable between v53 and v54: v54 rejects illegal moves before entering a child. Counts measure work done, not strength. The NNUE candidate's much lower throughput and one additional failed scored case do not justify making it the default. Its side-to-move feature convention is kept consistent with the embedded dense evaluator; no training data or network-quality claims are available.

## Fixed-depth ablation

`v54-depth.json` and `no-heuristics-depth.json` compare the same refactored engine with history, LMR and selective pruning enabled versus disabled. All eight scored cases pass in both variants. The enabled variant searched 16,020 nodes versus 20,884 (about **23% fewer**) and took 28.91 s versus 36.82 s in this run. These timings are environment-specific.

`v53-depth.json` is also retained. v54 is not uniformly faster than v53: its complete context handling, legal move validation and promotion coverage add work, and the selected search depths/extensions differ in effect. The measured tactical/rule improvements must not be represented as an overall speed or Elo gain.

## Validation beyond these comparisons

The test suite separately verifies perft totals 8,902 (initial position depth 3), 2,039 (Kiwipete depth 2), 2,812 (rook/pawn endgame depth 3), 264 and 1,486 (standard promotion/castling test positions depth 2), plus promotion perft against chess.js. It checks full scalar context restoration and frame sizes on normal, cutoff, TT-hit, node-limit, wall-time and maximum-ply returns, including a deliberately nested call at the same chess ply. Promotion tests exercise the controller, PGN, hashing and engine synchronization.

These checks do not replace large tactical suites, self-play matches, browser/GUI testing or TurboWarp compiler validation. Reverse futility, delta pruning and LMR remain selective heuristics with the usual possibility of missing deeper tactics; flags allow controlled ablations.
