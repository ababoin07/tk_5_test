'use strict';
// Benchmark-only normalization/instrumentation; not included in the distributed SB3.
module.exports=function profileProject(project,buckets){
 const target=project.targets.find(t=>t.name==='turboknight'),B=target.blocks;
 B['j_'].inputs.VALUE=[1,[4,String(buckets)]];
 target.variables.bench_duplicates=['bench.duplicates',0];
 let serial=0;
 for(const [id,b]of Object.entries(B)){
  if(b.opcode!=='procedures_call'||b.mutation.proccode!=='search.q_search %s %s %s')continue;
  let p=b.parent,definition=null;const seen=new Set();while(p&&!seen.has(p)){seen.add(p);if(B[p].opcode==='procedures_definition'){definition=B[p];break;}p=B[p].parent;}
  if(!definition||B[definition.inputs.custom_block[1]].mutation.proccode!=='search.negamax %s %s %s %s %s %b')continue;
  // v52 counts the same position in NEG and again in Q at depth zero. Record
  // these delegations so throughput is also reported in distinct position entries.
  const parent=B[b.parent],key='bench_delegation_'+(++serial);
  B[key]={opcode:'data_changevariableby',fields:{VARIABLE:['bench.duplicates','bench_duplicates']},inputs:{VALUE:[1,[4,'1']]},next:id,parent:b.parent,shadow:false,topLevel:false};
  if(parent.next===id)parent.next=key;else for(const value of Object.values(parent.inputs))if(value[1]===id)value[1]=key;
  b.parent=key;
 }
 return project;
};
