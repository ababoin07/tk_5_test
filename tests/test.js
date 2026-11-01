'use strict';
const assert=require('node:assert/strict');
const {Chess}=require('chess.js');
const {Engine,START,MAKE,ATTACK}=require('./runtime');
const FENS=[START,'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1','8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1','4k3/P7/8/8/8/8/7p/4K3 w - - 0 1','4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1','r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1','rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8'];
function oraclePerft(chess,d){if(!d)return 1;let n=0;for(const m of chess.moves({verbose:true})){chess.move(m);n+=oraclePerft(chess,d-1);chess.undo();}return n;}
(async()=>{
 const e=await Engine.load(process.argv[2]||'TurboKnight-5-v55.sb3');let tests=0;
 for(const fen of FENS){
  e.fen(fen);const before=e.snapshot();const actual=[];
  for(const m of e.moves()){
   e.call(MAKE,m);
   const names=['position.positionnal_hash','position.datas_hash','position.PSQT_mg_res','position.PSQT_eg_res','position.game_phase','position.pawns_count'];
   const incremental=names.map(n=>Number(e.get(n)));
   e.call('tools.get_positionnal_hash_slow');e.call('tools.get_datas_hash_slow');e.call('position.reset_evaluation');
   for(let i=0;i<names.length;i++)assert.ok(Math.abs(incremental[i]-e.get(names[i]))<0.01,`incremental ${names[i]} ${Engine.notation(m)} ${fen}`);
   const turn=Number(e.get('position.turn'));e.call(ATTACK,[e.get(turn===-1?'position.kw_pos':'position.kb_pos'),-turn]);
   if(!Number(e.get('tools.is_square_attacked.attacked')))actual.push(Engine.notation(m));
   e.call('position.unmake_move');assert.equal(e.snapshot(),before,'make/unmake');
  }
  assert.deepEqual(actual.sort(),new Chess(fen).moves({verbose:true}).map(m=>m.from+m.to+(m.promotion||'')).sort(),fen);tests++;
 }
 for(const fen of [
  '4r1k1/8/8/8/8/8/8/4K2R w K - 0 1', // castle out of check
  '5rk1/8/8/8/8/8/8/4K2R w K - 0 1', // castle through check
  '6r1/7k/8/8/8/8/8/4K2R w K - 0 1', // castle into check
  'k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', // pinned en passant
  '4r1k1/8/8/8/8/8/4R3/4K3 w - - 0 1' // pinned rook
 ]){
  e.fen(fen);const before=e.snapshot();const legal=e.moves().filter(m=>e.isLegal(m)).map(Engine.notation).sort();
  assert.deepEqual(legal,new Chess(fen).moves({verbose:true}).map(m=>m.from+m.to+(m.promotion||'')).sort(),fen);
  assert.equal(e.snapshot(),before);tests++;
 }
 e.fen('4r1k1/8/8/8/8/8/8/4K3 b - - 0 1');const probeBefore=e.snapshot();e.call('search.king_probe');assert.equal(Number(e.get('moves_generator.king_capture')),1);assert.equal(e.snapshot(),probeBefore);tests++;
 console.log('PASS legal moves, castling, pins, king disappearance + incremental state:',tests,'positions');
 for(const [fen,d,expected]of [[START,3,8902],[FENS[1],2,2039],[FENS[2],3,2812],[FENS[5],2,264],[FENS[6],2,1486],[FENS[3],2,null]]){
  e.fen(fen);const before=e.snapshot();e.call('__PERFT %s %s',[d,1]);assert.equal(e.value(),expected??oraclePerft(new Chess(fen),d));assert.equal(e.snapshot(),before);assert.equal(e.get('search.context.sp'),0);tests++;console.log('PASS perft',d,e.value());
 }
 for(const [name,fen,d,test]of [
  ['mate','7k/6Q1/6K1/8/8/8/8/8 b - - 0 1',1,v=>v===-10000000],
  ['mate in one','7k/8/5KQ1/8/8/8/8/8 w - - 0 1',2,v=>v===9999999],
  ['stalemate','7k/5K2/6Q1/8/8/8/8/8 b - - 0 1',0,v=>v===0],
  ['quiet evasion','4k3/8/8/8/8/8/8/K3R3 b - - 0 1',0,v=>Math.abs(v)<1000],
  ['rook underpromotion','8/k1P5/2K5/8/8/8/8/8 w - - 0 1',1,v=>v>300],
  ['fifty move','4k3/8/8/8/8/8/8/K3R3 b - - 100 1',2,v=>v===0],
  ['mate overrides fifty move','7k/6Q1/6K1/8/8/8/8/8 b - - 100 1',2,v=>v===-10000000]
 ]){
  e.fen(fen);e.clearTT();const before=e.snapshot();const value=e.search(d);assert.ok(test(value),name+' score '+value);assert.equal(e.snapshot(),before);assert.equal(e.get('search.context.sp'),0);
  if(name==='rook underpromotion')assert.equal(e.resultMove(),'c7c8r');console.log('PASS',name,value,e.resultMove());tests++;
 }
 // Every scalar in the context must restore, not just alpha/beta, even with nested timeouts.
 const stackNames=[...e.vars.keys()].filter(n=>n.startsWith('search.context.')&&Array.isArray(e.get(n)));
 const fields=stackNames.map(n=>n.replace('search.context.','search.'));
 for(const kind of ['normal','cutoff','TT hit','node timeout','wall timeout','max ply']){
  e.fen(START);e.clearTT();if(kind==='TT hit')e.search(3);
  fields.forEach((n,i)=>e.set(n,1000+i));const sentinel=fields.map(n=>e.get(n)),before=e.snapshot();const sizes=stackNames.map(n=>e.get(n).length);e.peak=0;
  if(kind==='node timeout')e.set('search.max_nodes',60);
  if(kind==='wall timeout'){e.set('search.start',0);e.set('search.max_time',0.01);}
  e.search(3,kind==='cutoff'?-50:-10000001,kind==='cutoff'?0:10000001,kind==='max ply'?128:1);
  assert.deepEqual(fields.map(n=>e.get(n)),sentinel,kind);assert.equal(e.get('search.context.sp'),0);assert.deepEqual(stackNames.map(n=>e.get(n).length),sizes);assert.equal(e.snapshot(),before);
  if(kind.includes('timeout'))assert.equal(Number(e.get('search.stopped')),1);console.log('PASS restore',kind,'peak',e.peak);tests++;
 }
 // A nested search at the SAME chess ply must use a different call-frame move buffer.
 e.fen(START);e.clearTT();e.set('search.context.sp',1);e.moves(1);
 const buffers=['start','end','flag0','flag1','score'].map(n=>e.get('search.moves.'+n).slice(0,512));
 e.search(2);assert.equal(e.get('search.context.sp'),1);
 assert.deepEqual(['start','end','flag0','flag1','score'].map(n=>e.get('search.moves.'+n).slice(0,512)),buffers);
 e.set('search.context.sp',0);tests++;console.log('PASS same-ply nested call preserves outer move frame');
 // Mate normalization through TT must survive reaching the SAME position at another root ply.
 e.fen('7k/8/5KQ1/8/8/8/8/8 w - - 0 1');e.clearTT();e.search(2,-10000001,10000001,5);const a=e.value();const b=e.search(2,-10000001,10000001,1);assert.equal(a,9999995);assert.equal(b,9999999);tests++;console.log('PASS TT mate normalization',a,b);
 // Cold iterative search, and fallback before any iteration completes.
 for(const cap of [0,1,100]){
  e.fen(START);e.clearTT();e.set('_dci',[]);e.set('_dci max nodes',cap);const before=e.snapshot();e.call('iterative_deepening %s %s',[30,3]);
  const output=e.get('_dci').at(-1);assert.ok(output.startsWith('m'));const move=output.slice(1);assert.ok(new Chess(START).moves({verbose:true}).some(m=>m.from+m.to+(m.promotion||'')===move),output);assert.equal(e.snapshot(),before);assert.equal(e.get('search.context.sp'),0);
  if(!cap)assert.equal(Number(e.get('search.completed_depth')),3);console.log('PASS iterative / fallback node limit',cap,move,e.get('search.completed_depth'));tests++;
 }
 // Opening-book moves are checked for legality; invalid entries fall back to search.
 for(const [bookMove,accept]of [['e2e4',true],['h1h8',false]]){
  e.fen(START);e.clearTT();e.set('search.use_book',1);e.set('_OPENING_BOOK',[Number(e.get('position.positionnal_hash'))+Number(e.get('position.datas_hash')),bookMove]);e.set('_dci',[]);const before=e.snapshot();
  e.call('iterative_deepening %s %s',[10,1]);const move=e.get('_dci').at(-1).slice(1);
  if(accept)assert.equal(move,bookMove);else assert.notEqual(move,bookMove);
  assert.ok(new Chess(START).moves({verbose:true}).some(m=>m.from+m.to===move));assert.equal(e.snapshot(),before);assert.equal(e.get('search.context.sp'),0);tests++;console.log('PASS opening book validation',bookMove,move);
 }
 // Sparse NNUE reproduces the uploaded dense network; this does not establish chess strength.
 for(const fen of [START,FENS[2],FENS[3]]){e.fen(fen);e.call('nnue.init_accumulator');const dense=e.get('nnue.accumulator').map(Number);e.call('nnue.sparse_refresh');const sparse=e.get('nnue.accumulator').map(Number);assert.ok(dense.every((x,i)=>Math.abs(x-sparse[i])<1e-9));tests++;}
 console.log('ALL PASSED',tests,'test groups');process.stdout.write('',()=>process.exit(0));
})().catch(e=>{console.error(e);process.exit(1)});
