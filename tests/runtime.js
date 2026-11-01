'use strict';
const fs = require('node:fs');
const VM = require('scratch-vm');
const JSZip = require('jszip');
const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const NEG = 'search.negamax %s %s %s %s %s %b';
const GEN = 'moves_generator.get_moves %s %b';
const MAKE = 'position._make_move_impl %s %s %s %s';
const ATTACK = 'tools.is_square_attacked %s %s';
const POS = ['position.board','position.turn','position.kw_pos','position.kb_pos','position.en_passant_square','position.white_castle_king_side','position.white_castle_queen_side','position.black_castle_king_side','position.black_castle_queen_side','position.half_moves','position.full_moves','position.positionnal_hash','position.datas_hash','position.PSQT_mg_res','position.PSQT_eg_res','position.game_phase','position.pawns_count','_plies_from_begining'];
class Engine {
    static async load(file) {
        const e = new Engine();
        const zip = await JSZip.loadAsync(fs.readFileSync(file));
        e.project = JSON.parse(await zip.file('project.json').async('string'));
        const p = structuredClone(e.project);
        // Preserve costume NAMES/counts for the FEN importer; substitute payloads only in memory.
        for (const t of p.targets) { t.costumes = t.costumes.map(c => ({...c,assetId:'cd21514d0531fdffb22204e0ec5ed84a',md5ext:'cd21514d0531fdffb22204e0ec5ed84a.svg',dataFormat:'svg'}));t.sounds=[]; }
        e.vm = new VM();e.vm.runtime.currentStepTime=20;e.vm.setTurboMode(true);
        const oldWarn = console.warn, oldLog=console.log;
        console.warn=console.log=()=>{};
        try { await e.vm.loadProject(JSON.stringify(p)); } finally {console.warn=oldWarn;console.log=oldLog;}
        e.target=e.vm.runtime.targets.find(t=>t.getName()==='turboknight');e.stage=e.vm.runtime.getTargetForStage();
        e.vars=new Map(Object.values(e.stage.variables).map(v=>[v.name,v]));
        for(const v of Object.values(e.target.variables))e.vars.set(v.name,v);
        e.vm.runtime._primitives.event_broadcast=()=>{};e.vm.runtime._primitives.event_broadcastandwait=()=>{};
        e.serial=0;e.peak=0;
        const replace=e.vm.runtime._primitives.data_replaceitemoflist;
        e.vm.runtime._primitives.data_replaceitemoflist=(a,u)=>{
            const v=u.target.lookupVariableById(a.LIST.id);
            if(v && /^search\.(context\.|moves\.)/.test(v.name)) {
                const i=Number(a.INDEX);
                if(i<1 || i>v.value.length || !Number.isInteger(i))throw Error(`Out-of-range ${v.name}[${i}], length=${v.value.length}`);
                if(v.name.startsWith('search.context.'))e.peak=Math.max(e.peak,i);
            }
            return replace(a,u);
        };
        e.call('engine.init');e.modern=e.vars.has('search.result.value');
        return e;
    }
    get(n){if(!this.vars.has(n))throw Error('Unknown variable '+n);return this.vars.get(n).value;}
    set(n,x){if(!this.vars.has(n))throw Error('Unknown variable '+n);this.vars.get(n).value=x;}
    optional(n,x){if(this.vars.has(n))this.set(n,x);}
    call(code,args=[],target=this.target) {
        const blocks=target.blocks;
        const proto=Object.values(blocks._blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode===code);
        if(!proto)throw Error('Unknown procedure '+code);
        const id='test_'+(++this.serial),ids=JSON.parse(proto.mutation.argumentids),inputs={},created=[];
        for(let i=0;i<ids.length;i++){
            const bid=id+'_'+i;const mk=(id,opcode,fields,inputs)=>{blocks.createBlock({id,opcode,fields,inputs,next:null,parent:bid,shadow:true,topLevel:false});created.push(id);};
            if(typeof args[i]==='boolean'){
                mk(bid+'a','text',{TEXT:{name:'TEXT',value:'1'}},{});
                mk(bid+'b','text',{TEXT:{name:'TEXT',value:args[i]?'1':'0'}},{});
                mk(bid,'operator_equals',{}, {OPERAND1:{name:'OPERAND1',block:bid+'a',shadow:bid+'a'},OPERAND2:{name:'OPERAND2',block:bid+'b',shadow:bid+'b'}});
            } else mk(bid,'text',{TEXT:{name:'TEXT',value:String(args[i]??'')}},{});
            inputs[ids[i]]={name:ids[i],block:bid,shadow:bid};
        }
        blocks.createBlock({id,opcode:'procedures_call',inputs,fields:{},next:null,parent:null,shadow:false,topLevel:true,mutation:{...proto.mutation}});created.push(id);
        const thread=this.vm.runtime._pushThread(id,target),start=Date.now();
        while(this.vm.runtime.threads.includes(thread)&&thread.status!==4){this.vm.runtime._step();if(Date.now()-start>120000)throw Error('Harness timeout '+code);}
        this.vm.runtime.threads=this.vm.runtime.threads.filter(t=>t!==thread);
        for(const k of created)blocks.deleteBlock(k);
    }
    fen(f) {
        this.set('tools.from_list_fen_importer.data',f.split(' '));this.call('tools.from_list_fen_importer');
        this.set('search.nodes',0);this.optional('search.qnodes',0);this.set('search.start',(Date.now()-Date.UTC(2000,0,1))/86400000);
        this.set('search.max_time',120);this.set('search.stopped',0);this.optional('search.max_nodes',0);this.optional('search.use_book',0);this.optional('_dci max nodes',0);
    }
    clearTT(){for(const name of ['tt.hash','tt.depth'])this.set(name,this.get(name).map(()=>name==='tt.hash'?0:-1));}
    snapshot(){return JSON.stringify(POS.map(n=>[n,Array.isArray(this.get(n))?this.get(n).map(Number):Number(this.get(n))]));}
    value(){return Number(this.modern?this.get('search.result.value'):this.get('search.best_value')[0]);}
    search(depth,alpha=-10000001,beta=10000001,ply=1){this.call(NEG,[ply,depth,alpha,beta,0,true]);return this.value();}
    resultMove(){if(this.modern){const from=Number(this.get('search.result.from'));if(!from)return '0000';const to=Number(this.get('search.result.to')),flag=Number(this.get('search.result.flag1'));return Engine.square(from)+Engine.square(to)+(flag>5?'nbrq'[flag-6]:'');}this.call('TT.probe');const from=Number(this.get('tt.probe.move.start'));return from?Engine.square(from)+Engine.square(Number(this.get('tt.probe.move.end')))+(Number(this.get('tt.probe.move.flag1'))>5?'nbrq'[Number(this.get('tt.probe.move.flag1'))-6]:''):'0000';}
    moves(frame=1){this.call(GEN,[frame,false]);const count=Number(this.get('moves_generator.get_moves.moves_count_res')),base=(frame-1)*512;return Array.from({length:count},(_,i)=>['start','end','flag0','flag1'].map(n=>Number(this.get((this.modern?'search.moves.':'moves_generator.')+n)[base+i])));}
    isLegal(m){this.call(MAKE,m);const turn=Number(this.get('position.turn'));this.call(ATTACK,[this.get(turn===-1?'position.kw_pos':'position.kb_pos'),-turn]);const legal=Number(this.get('tools.is_square_attacked.attacked'))===0;this.call('position.unmake_move');return legal;}
    static square(i){return 'abcdefgh'[(i-1)%8]+(8-Math.floor((i-1)/8));}
    static notation(m){return Engine.square(m[0])+Engine.square(m[1])+(m[3]>5?'nbrq'[m[3]-6]:'');}
}
module.exports={Engine,START,NEG,GEN,MAKE,ATTACK};
