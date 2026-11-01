'use strict';
const fs=require('node:fs');const assert=require('node:assert/strict');const JSZip=require('jszip');
(async()=>{
 const a=await JSZip.loadAsync(fs.readFileSync('baseline/TurboKnight-5-v53.sb3')),z=await JSZip.loadAsync(fs.readFileSync('TurboKnight-5-v54.sb3'));
 for(const n of Object.keys(a.files))if(n!=='project.json')assert.ok((await a.file(n).async('nodebuffer')).equals(await z.file(n).async('nodebuffer')),'asset '+n);
 const p=JSON.parse(await z.file('project.json').async('string')),engine=p.targets.find(t=>t.name==='turboknight');
 const lists=new Map(p.targets.flatMap(t=>Object.entries(t.lists).map(([id,[name,items]])=>[id,{name,items}])));
 const names=[...lists.values()].map(v=>v.name);
 for(const name of ['alpha','beta','best_value','move_idx','best_move_idx','is_kw_attacked','is_kb_attacked','stand_pat','first_move_idx','reduction','extension','TT_activated','killer_moves'])assert.ok(!names.includes('search.'+name),'old depth array '+name);
 assert.equal(names.filter(n=>n.startsWith('search.context.')).length,29);
 for(const t of p.targets){
  const B=t.blocks;
  for(const [id,b]of Object.entries(B)){
   if(b.next)assert.ok(B[b.next],id+' next');
   for(const v of Object.values(b.inputs))for(const r of v.slice(1))if(typeof r==='string')assert.ok(B[r],id+' input '+r);
   const list=b.fields?.LIST&&lists.get(b.fields.LIST[1]);
   if(list&&/^search\.(context\.|moves\.)/.test(list.name)){
    if(b.opcode==='data_itemoflist'||b.opcode==='data_replaceitemoflist'){
     const seen=new Set();function visit(v){if(Array.isArray(v)){for(const x of v)visit(x);}else if(typeof v==='string'&&B[v]&&!seen.has(v)){seen.add(v);const x=B[v];if(x.opcode.startsWith('argument_reporter'))assert.ok(!/depth|PLIES/i.test(x.fields.VALUE[0]),list.name+' uses depth');for(const input of Object.values(x.inputs))visit(input);}}
     visit(b.inputs.INDEX);
    }
    if(list.name.startsWith('search.context.'))assert.ok(!['data_addtolist','data_deleteoflist','data_deletealloflist'].includes(b.opcode),'context resizing');
   }
  }
 }
 assert.ok(engine.variables[Object.keys(engine.variables).find(k=>engine.variables[k][0]==='search.use_nnue')][1]===0,'NNUE default');
 console.log('PASS assets, block graph, 29 scalar context stacks, no depth arrays or depth-offset move access; NNUE disabled by default');
})().catch(e=>{console.error(e);process.exit(1)});
