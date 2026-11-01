'use strict';
const fs=require('node:fs');const {performance}=require('node:perf_hooks');const {Chess}=require('chess.js');const {Engine}=require('./runtime');const positions=require('./positions');
(async()=>{
 const file=process.argv[2]||'TurboKnight-5-v55.sb3';const mode=process.argv[3]||'depth';const out=process.argv[4];
 const e=await Engine.load(file);const rows=[];
 for(const p of positions){
  e.fen(p.fen);e.clearTT();e.optional('search.history',Array(8192).fill(0));e.set('_dci',[]);e.set('_OPENING_BOOK',[]);
  if(mode==='time'){
   const start=performance.now();e.call('iterative_deepening %s %s',[0.5,64]);const ms=performance.now()-start,move=e.get('_dci').filter(s=>typeof s==='string'&&s.startsWith('m')&&!s.startsWith('mate')).at(-1)?.slice(1)||'0000';
   const legal=new Chess(p.fen).moves({verbose:true}).some(m=>m.from+m.to+(m.promotion||'')===move);
   rows.push({name:p.name,ms:+ms.toFixed(2),nodes:Number(e.get('search.nodes')),depth:Number(e.modern?e.get('search.completed_depth'):e.get('iterative_deepening.depth')),move,legal,solved:p.best?p.best.includes(move):null});
  } else {
   const start=performance.now();const value=e.search(p.depth),ms=performance.now()-start,move=e.resultMove();
   const legal=new Chess(p.fen).moves({verbose:true}).some(m=>m.from+m.to+(m.promotion||'')===move);
   rows.push({name:p.name,ms:+ms.toFixed(2),nodes:Number(e.get('search.nodes')),depth:p.depth,value,move,legal,solved:p.best?p.best.includes(move):null});
  }
  console.log(rows.at(-1));
 }
 const report={artifact:file,artifact_sha256:require('node:crypto').createHash('sha256').update(fs.readFileSync(file)).digest('hex'),mode,node:process.version,platform:process.platform,positions:rows,summary:{solved:rows.filter(r=>r.solved===true).length,scored:rows.filter(r=>r.solved!==null).length,illegal:rows.filter(r=>!r.legal).length,nodes:rows.reduce((n,r)=>n+r.nodes,0),milliseconds:+rows.reduce((n,r)=>n+r.ms,0).toFixed(2)}};
 if(out)fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log('SUMMARY',report.summary);process.stdout.write('',()=>process.exit(0));
})().catch(e=>{console.error(e);process.exit(1)});
