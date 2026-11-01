'use strict';
const fs=require('node:fs');const assert=require('node:assert/strict');const JSZip=require('jszip');
(async()=>{
 const a=await JSZip.loadAsync(fs.readFileSync('baseline/TurboKnight-5-v53.sb3')),z=await JSZip.loadAsync(fs.readFileSync('TurboKnight-5-v56.sb3'));
 for(const n of Object.keys(a.files))if(n!=='project.json')assert.ok((await a.file(n).async('nodebuffer')).equals(await z.file(n).async('nodebuffer')),'asset '+n);
 const p=JSON.parse(await z.file('project.json').async('string')),engine=p.targets.find(t=>t.name==='turboknight');
 const lists=new Map(p.targets.flatMap(t=>Object.entries(t.lists).map(([id,[name,items]])=>[id,{name,items}])));
 const names=[...lists.values()].map(v=>v.name);
 const definitions=new Map(Object.values(engine.blocks).filter(b=>b.opcode==='procedures_definition').map(d=>[engine.blocks[d.inputs.custom_block[1]].mutation.proccode,d.next]));
 for(const name of ['search.king_probe','search.probe_check']){
  const seen=new Set();function visit(id){if(!id||seen.has(id))return;seen.add(id);const b=engine.blocks[id];if(b.opcode==='procedures_call'){assert.ok(!b.mutation.proccode.startsWith('moves_generator.get_moves'),'king status must not generate reply lists');if(definitions.has(b.mutation.proccode))visit(definitions.get(b.mutation.proccode));}visit(b.next);for(const v of Object.values(b.inputs))for(const r of v.slice(1))if(typeof r==='string')visit(r);}
  visit(definitions.get(name));
 }

 assert.ok(!Object.values(engine.blocks).some(b=>b.opcode==='procedures_call'&&b.mutation.proccode==='tools.is_square_attacked %s %s'),'search must use king-disappearance probes');
 for(const b of Object.values(engine.blocks)){if(!['event_broadcast','event_broadcastandwait'].includes(b.opcode))continue;const input=b.inputs.BROADCAST_INPUT;assert.equal(input[0],1,'generated broadcasts must use literal menu shadows');assert.equal(input[1][0],11);assert.equal(p.targets[0].broadcasts[input[1][2]],input[1][1]);}

 for(const name of ['alpha','beta','best_value','move_idx','best_move_idx','is_kw_attacked','is_kb_attacked','stand_pat','first_move_idx','reduction','extension','TT_activated','killer_moves'])assert.ok(!names.includes('search.'+name),'old depth array '+name);
 assert.equal(names.filter(n=>n.startsWith('search.context.')).length,26);
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
 console.log('PASS assets, block graph, 26 scalar context stacks, no depth arrays or depth-offset move access; NNUE disabled by default');
})().catch(e=>{console.error(e);process.exit(1)});
