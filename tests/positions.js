const {START}=require('./runtime');
module.exports=[
 {name:'start',fen:START,depth:3},
 {name:'kiwipete',fen:'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1',depth:2},
 {name:'rook-endgame',fen:'8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1',depth:4},
 {name:'mate-in-one',fen:'7k/8/5KQ1/8/8/8/8/8 w - - 0 1',depth:2,best:['g6g7']},
 {name:'back-rank-white',fen:'7k/6pp/8/8/8/8/8/R5K1 w - - 0 1',depth:3,best:['a1a8']},
 {name:'back-rank-black',fen:'r5k1/8/8/8/8/8/6PP/7K b - - 0 1',depth:3,best:['a8a1']},
 {name:'rook-underpromotion',fen:'8/k1P5/2K5/8/8/8/8/8 w - - 0 1',depth:1,best:['c7c8r']},
 {name:'take-queen-rook',fen:'6k1/8/8/3q4/8/8/3R4/6K1 w - - 0 1',depth:3,best:['d2d5']},
 {name:'take-queen-knight',fen:'4k3/8/8/3q4/8/2N5/8/4K3 w - - 0 1',depth:3,best:['c3d5']},
 {name:'capture-promotion',fen:'r3k3/1P6/8/8/8/8/8/4K3 w - - 0 1',depth:2,best:['b7a8q']},
 {name:'en-passant',fen:'4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',depth:3},
 {name:'quiet-check-evasion',fen:'4k3/8/8/8/8/8/8/K3R3 b - - 0 1',depth:2,best:['e8d8','e8d7','e8f8','e8f7']}
];
