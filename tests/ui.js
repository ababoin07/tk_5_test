'use strict';
const assert=require('node:assert/strict');const {Engine}=require('./runtime');
(async()=>{
 const e=await Engine.load('TurboKnight-5-v56.sb3');const d=e.vm.runtime.targets.find(t=>t.getName()==='deltaci');const local=n=>Object.values(d.variables).find(v=>v.name===n);const fen='4k2r/P7/8/8/8/8/8/4K3 w - - 0 1';
 for(const [suffix,dci,engine]of [['n',3,2],['b',3.1,3],['r',5,4],['q',9,5]]){
  local('dci fen').value=fen;e.set('_dci fen',fen);e.call('FEN to state',[],d);e.fen(fen);local('dci auto respond').value=0;
  e.call('io handler %s %s',['m','ma7a8'+suffix],d);
  assert.equal(Number(e.get('_dci board')[0]),dci,'DCI promotion '+suffix);
  assert.ok(local('dci pgn').value.at(-1).endsWith('='+suffix.toUpperCase()),'PGN promotion');
  e.call('position.make_move_uci %s %s',[9,1]);assert.equal(Number(e.get('position.board')[0]),engine,'engine GUI sync '+suffix);
  const a=Number(local('dci board hash').value);e.call('dci.rehash',[],d);assert.equal(Number(local('dci board hash').value),a,'DCI promotion hash');
  local('dci fen').value=e.get('_dci fen');e.call('FEN to state',[],d);assert.equal(Number(local('dci board hash').value),a,'FEN rebuild must match promotion hash');
  console.log('PASS GUI/DCI promotion and engine synchronization',suffix);
 }
 process.stdout.write('',()=>process.exit(0));
})().catch(e=>{console.error(e);process.exit(1)});
