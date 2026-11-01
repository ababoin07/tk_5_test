'use strict';
const fs=require('node:fs'),{chromium}=require('playwright');
const {server,load,answer,clickMove,setBrowser}=require('./browser');
let browser;
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});setBrowser(browser);
 const report={runtime:'compiled TurboWarp, real GUI and broadcasts active',tt_buckets:50000,thinking_time:0.5,repetitions:3,notes:'Opening book cleared. Same TT capacity as kernel benchmark. First run warms compilation; three following games measured. Wall time includes controller/GUI delivery after the player move. Raw nodes reflect each version’s search. The original counts the same depth-zero position in NEG and Q; the corrected position-entry measure subtracts these delegations (at a timeout boundary its error can be one entry). No release node counter is changed.',variants:[]};
 for(const file of ['baseline/TurboKnight-5-v52.sb3','TurboKnight-5-v55.sb3','TurboKnight-5-v56.sb3']){
  const {page,errors}=await load(file,{ttBuckets:50000});const samples=[];
  for(let rep=0;rep<4;rep++){
   if(rep)await page.evaluate(()=>vm.greenFlag());await answer(page,0.5);
   await page.evaluate(()=>{const stage=vm.runtime.getTargetForStage();Object.values(stage.variables).find(v=>v.name==='_OPENING_BOOK').value=[];const engine=vm.runtime.targets.find(t=>t.getName()==='turboknight');Object.values(engine.variables).find(v=>v.name==='bench.duplicates').value=0;});
   const start=Date.now();await clickMove(page,'e2','e4');await page.waitForFunction(()=>state().turn===1&&state().messages.filter(m=>/^m[a-h][1-8][a-h][1-8][nbrq]?$/.test(m)).length>=2,null,{timeout:30000});
   const s=await page.evaluate(()=>state()),ms=Date.now()-start;
   if(s.compileErrors.length||errors.length)throw Error(JSON.stringify({errors,compile:s.compileErrors}));
   if(rep)samples.push({ms,nodes:s.nodes,delegations:s.delegations,positions:s.nodes-s.delegations,position_nps:(s.nodes-s.delegations)*1000/ms,nps:s.nodes*1000/ms,depth:s.depth});
  }
  const result={file,sha256:require('node:crypto').createHash('sha256').update(fs.readFileSync(file)).digest('hex'),samples,median_position_nps:samples.map(s=>s.position_nps).sort((a,b)=>a-b)[1],median_nps:samples.map(s=>s.nps).sort((a,b)=>a-b)[1]};report.variants.push(result);console.log(result);await page.close();
 }
 fs.writeFileSync('benchmarks/gui-speed-v56.json',JSON.stringify(report,null,2)+'\n');await browser.close();server.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();server.close();process.exitCode=1;});
