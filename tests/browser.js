'use strict';
// Real renderer, compiler, broadcasts, question prompt and mouse polling. No VM primitive stubs.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright');const {Chess}=require('chess.js');
const ROOT=path.resolve(__dirname,'..');
const profileSource=require('./profile-project').toString();
const runtime=require.resolve('@turbowarp/packager/dist/scaffolding/scaffolding-min.js');
const server=http.createServer((req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname==='/favicon.ico'){res.statusCode=204;res.end();return;}
 if(url.pathname==='/'){
  res.setHeader('Content-Type','text/html');
  res.end('<meta charset="utf-8"><div id="project" style="width:480px;height:360px"></div><script src="/runtime.js"></script>');return;
 }
 const file=url.pathname==='/runtime.js'?runtime:path.join(ROOT,decodeURIComponent(url.pathname));
 if(!file.startsWith(ROOT+path.sep)&&file!==runtime){res.statusCode=403;res.end();return;}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':'application/octet-stream');
 fs.createReadStream(file).on('error',()=>{res.statusCode=404;res.end();}).pipe(res);
});
let browser;
async function load(file,options={}){
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:'+server.address().port+'/');
 await page.evaluate(async({file,ttBuckets,profileSource})=>{
  window.player=new Scaffolding.Scaffolding();player.setup();player.appendTo(document.getElementById('project'));
  window.vm=player.vm;window.compileErrors=[];window.compiledTargets=[];
  vm.runtime.on('COMPILE_ERROR',(...args)=>compileErrors.push(args.map(a=>a?.message||String(a))));
  const step=vm.runtime.sequencer.stepThread;
  vm.runtime.sequencer.stepThread=function(thread){const result=step.call(this,thread);if(thread.isCompiled&&!compiledTargets.includes(thread.target.getName()))compiledTargets.push(thread.target.getName());return result;};
  window.state=()=>{
   const stage=vm.runtime.getTargetForStage(),engine=vm.runtime.targets.find(t=>t.getName()==='turboknight');
   const get=(target,name)=>Object.values(target.variables).find(v=>v.name===name)?.value;
   return {turn:Number(get(stage,'_dci turn')),player:Number(get(stage,'_dci player')),time:get(stage,'_dci think time'),
    messages:[...get(stage,'_dci')],board:[...get(stage,'_dci board')].map(Number),engineBoard:[...get(engine,'position.board')].map(Number),
    engineTurn:Number(get(engine,'position.turn')),sp:Number(get(engine,'search.context.sp')),nodes:Number(get(engine,'search.nodes')),delegations:Number(get(engine,'bench.duplicates')||0),
    depth:Number(get(engine,'search.completed_depth')??get(engine,'iterative_deepening.depth')),compileErrors,compiledTargets};
  };
  let data=await(await fetch('/'+file)).arrayBuffer();if(ttBuckets){const zip=await Scaffolding.JSZip.loadAsync(data);const project=JSON.parse(await zip.file('project.json').async('string'));(0,eval)('('+profileSource+')')(project,ttBuckets);zip.file('project.json',JSON.stringify(project));data=await zip.generateAsync({type:'uint8array'});}await player.loadProject(data);player.start();
 },{file,ttBuckets:options.ttBuckets,profileSource});
 return {page,errors};
}
async function answer(page,time){
 const input=page.locator('input:visible');await input.waitFor({timeout:30000});await input.fill(String(time));await input.press('Enter');
 await page.waitForFunction(time=>state().time===String(time),time,{timeout:10000});
}
async function clickMove(page,from,to){
 const box=await page.locator('canvas').boundingBox();
 for(const square of [from,to]){
  const file=square.charCodeAt(0)-97,rank=Number(square[1]);
  await page.mouse.click(box.x+50+40*file,box.y+40+40*(8-rank),{delay:90});
  await page.waitForTimeout(60); // The original GUI polls mouse state; instantaneous clicks may be missed.
 }
}
function checkBoards(s){
 const pieces=[0,1,3,3.1,5,9,100];
 assert.deepEqual(s.board,s.engineBoard.map(p=>Math.sign(p)*pieces[Math.abs(p)]),'controller/engine board synchronization');
 assert.equal(s.turn,s.engineTurn);assert.equal(s.sp,0);assert.equal(s.turn,1);assert.deepEqual(s.compileErrors,[]);
 const chess=new Chess();for(const command of s.messages.filter(m=>/^m[a-h][1-8][a-h][1-8][nbrq]?$/.test(m)))chess.move({from:command.slice(1,3),to:command.slice(3,5),promotion:command[5]});
 assert.equal(chess.turn(),'w','engine must reply with a legal black move');
}
async function waitReply(page,plies){
 await page.waitForFunction(plies=>state().turn===1&&state().messages.filter(m=>/^m[a-h][1-8][a-h][1-8][nbrq]?$/.test(m)).length>=plies,plies,{timeout:30000});
 const s=await page.evaluate(()=>state());checkBoards(s);return s;
}
async function main(){
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const executablePath=process.env.CHROMIUM_PATH||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined);
 browser=await chromium.launch({executablePath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 // Negative control: the previously shipped file computes a reply but never broadcasts it to the GUI.
 {
  const {page}=await load('TurboKnight-5-v54.sb3');await answer(page,0.05);await clickMove(page,'e2','e4');
  await page.waitForFunction(()=>state().messages.some(m=>/^m[a-h]7[a-h][1-6]/.test(m)),null,{timeout:10000});
  await page.waitForTimeout(250);const s=await page.evaluate(()=>state());assert.equal(s.turn,-1,'v54 negative control must reproduce the stalled GUI');
  console.log('PASS negative control: v54 computes a reply but remains on Black’s turn');await page.close();
 }
 const {page,errors}=await load('TurboKnight-5-v56.sb3');await answer(page,0.05);
 await clickMove(page,'e2','e4');let s=await waitReply(page,2);assert.ok(s.compiledTargets.includes('turboknight'),'engine scripts must run compiled');
 console.log('PASS compiled GUI: enter thinking time, e2e4, Black replies, White can move again');
 // Force actual search for the second move, rather than allowing opening-book-only coverage.
 await page.evaluate(()=>{const t=vm.runtime.targets.find(t=>t.getName()==='turboknight');Object.values(t.variables).find(v=>v.name==='search.use_book').value=0;});
 await clickMove(page,'g1','f3');s=await waitReply(page,4);assert.ok(s.nodes>0,'search must execute');
 console.log('PASS compiled GUI: second player move triggers search and a synchronized reply',JSON.stringify({nodes:s.nodes,depth:s.depth}));
 // A second game must not reuse a stale engine position, frame pointer, or turn.
 await page.evaluate(()=>vm.greenFlag());await answer(page,0.05);
 await page.evaluate(()=>{const t=vm.runtime.targets.find(t=>t.getName()==='turboknight');Object.values(t.variables).find(v=>v.name==='search.use_book').value=0;});
 await clickMove(page,'d2','d4');s=await waitReply(page,2);assert.ok(s.nodes>0);assert.deepEqual(errors,[]);
 console.log('PASS compiled GUI: restart, enter thinking time, d2d4 and legal search reply');
 await page.screenshot({path:path.join(ROOT,'build/v56-gui.png')});
 await browser.close();server.close();
}
module.exports={server,load,answer,clickMove,waitReply,setBrowser:b=>{browser=b;}};
if(require.main===module)main().catch(async e=>{console.error(e);if(browser)await browser.close();server.close();process.exitCode=1;});
