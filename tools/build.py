#!/usr/bin/env python3
"""Build v56 from the asset-preserving v53 baseline. No Scratch or TurboWarp extensions required."""
import argparse,copy,json,pathlib,zipfile
from blocks import *
ROOT=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'TurboKnight-5-v56.sb3'));parser.add_argument('--no-history',action='store_true');parser.add_argument('--no-lmr',action='store_true');parser.add_argument('--no-pruning',action='store_true');parser.add_argument('--nnue',action='store_true');args=parser.parse_args()
archive=zipfile.ZipFile(ROOT/'baseline/TurboKnight-5-v53.sb3');P=json.loads(archive.read('project.json'));T=P['targets'][-1];b=Builder(P,T);B=b.B
# Baseline call mutations omit argumentnames/argumentdefaults, which breaks the
# TurboWarp editor. Backfill them from each procedure's prototype before editing;
# prototypes with stale defaults are normalized to their own argument count.
def normalize_mutation(m):
    ids=json.loads(m['argumentids'])
    types=[x for x in m['proccode'].split() if x in ('%s','%n','%b')]
    def valid(field):
        try:parsed=json.loads(m[field])
        except Exception:return None
        return parsed if isinstance(parsed,list) and len(parsed)==len(ids) else None
    names=valid('argumentnames')
    if names is None:m['argumentnames']=json.dumps(['arg'+str(i+1) for i in range(len(ids))])
    defaults=valid('argumentdefaults')
    if defaults is None:
        vals=['' if t!='%b' else 'false' for t in types[:len(ids)]]
        m['argumentdefaults']=json.dumps(vals+['']*(len(ids)-len(vals)))
protos={}
for t in P['targets']:
    for v in t['blocks'].values():
        if v['opcode']=='procedures_prototype':
            normalize_mutation(v['mutation']);protos.setdefault(v['mutation']['proccode'],v['mutation'])
for t in P['targets']:
    for v in t['blocks'].values():
        if v['opcode']!='procedures_call':continue
        m=v['mutation'];p=protos.get(m['proccode'])
        if p is not None and json.loads(p['argumentids'])==json.loads(m['argumentids']):
            m['argumentnames']=p['argumentnames'];m['argumentdefaults']=p['argumentdefaults']
        normalize_mutation(m)
CAP=132;MOVES=512;MATE=10000000;INF=MATE+1
# Search-margin tunables, single source of truth for both RFP sites.
LMR_BASE=1.35   # LMR constant reduction applied to the first late move
LMR_DIV=2.75    # divisor of the ln(ordinal)*ln(depth) LMR term
RFP_BASE=120    # reverse futility pruning base margin (centipawns)
RFP_COEF=30     # reverse futility margin added per depth^2
NEG='search.negamax %s %s %s %s %s %b';Q='search.q_search %s %s %s';PERFT='__PERFT %s %s';GEN='moves_generator.get_moves %s %b';MAKE='position._make_move_impl %s %s %s %s';ATTACK='tools.is_square_attacked %s %s';NOTATION='tools._get_uci_notation_impl %s %s %s %s';STORE='TT.store %s %s %s %s %s %s %s %s';ITER='iterative_deepening %s %s'
# Remove all earlier search implementations, including per-ply killers and wrappers.
for k,v in list(B.items()):
    if v['opcode']=='procedures_definition':
        code=B[v['inputs']['custom_block'][1]]['mutation']['proccode']
        if code.startswith(('search.','iterative_deepening','__PERFT','killer_moves.')):del B[k]
# Remove depth-indexed node arrays. Surviving UCI references use the explicit return value.
old_lists={}
for t in P['targets']:
    for k,v in list(t['lists'].items()):
        if v[0].startswith('search.'):
            old_lists[k]=v[0];del t['lists'][k]
for v in B.values():
    f=v.get('fields',{}).get('LIST')
    if f and f[1] in old_lists:
        name='search.result.value' if f[0]=='search.best_value' else f[0]
        v['fields']={'VARIABLE':[name,b.variable(name)]}
        if v['opcode']=='data_itemoflist':v['opcode']='data_variable';v['inputs']={}
        elif v['opcode'] in ('data_addtolist','data_replaceitemoflist','data_deletealloflist'):
            v['opcode']='data_setvariableto';v['inputs']={'VALUE':b.input(0)}
        else:raise ValueError(v)
# Move buffers belong to call frames, never to a ply. Their generator accepts a frame number.
rename={'moves_generator.'+n:'search.moves.'+n for n in ('start','end','flag0','flag1')};rename['tools.quicksort.scores']='search.moves.score'
for t in P['targets']:
    for k,v in t['lists'].items():
        if v[0] in rename:v[0]=rename[v[0]]
for v in B.values():
    f=v.get('fields',{}).get('LIST')
    if f and f[0] in rename:f[0]=rename[f[0]]
# Replace two stale argument reporters for a parameter engine.init does not declare.
B['fe']['inputs']['VALUE']=b.input(64)
B['j_']['inputs']['VALUE']=b.input(50000)
B['Ak']['inputs']['ITEM']=b.input('id name TurboKnight 5 v56')
# Existing init preallocates the move buffers. Give it two spare frames past the ply cap.
B['aZ']['inputs']['TIMES']=b.input(CAP*MOVES)
# Eliminate stale or undeclared removed procedure references on non-procedure debug scripts.
# The remaining public entry names/argument IDs stay compatible with all existing callers.
fields=['ply','depth','alpha','beta','alpha_start','beta_start','extension','tt_allowed','base','move_idx','best_value','best_from','best_to','best_flag0','best_flag1','in_check','legal_count','from','to','flag0','flag1','reduction','static','is_pv','rfp','previous_legal','gives_check','count','score','legal','drawn','skip','gain','history_idx','bonus']
s=lambda n:V('search.'+n)
setv=lambda n,x:b.set('search.'+n,x)
inc=lambda n,x=1:b.inc('search.'+n,x)
li=b.item
for n in fields:b.variable('search.'+n);b.newlist('search.context.'+n,CAP)
b.newlist('search.history',8192);b.newlist('data.material',6)
T['lists'][b.listid('data.material')][1]=[100,320,330,500,900,20000]
for n,val in {'search.context.sp':0,'search.context.capacity':CAP,'search.use_history':int(not args.no_history),'search.use_lmr':int(not args.no_lmr),'search.use_nnue':int(args.nnue),'search.use_pruning':int(not args.no_pruning),'search.use_book':1,'search.max_nodes':0}.items():T['variables'][b.variable(n)][1]=val
for code,names in {'search.context.push':[],'search.context.pop':[],'search.node':[],'search.quiescence':[],'search.evaluate':[],'search.king_probe':[],'search.probe_check':[],'search.legal_witness':[],'search.check':[],'search.try_move':[],'search.load_move':[],'search.order':[],'search.tt_probe':[],'search.tt_store':[],'search.limits':[],'search.draw':[],'search.root_fallback %s':['wanted'],'search.emit':[],'nnue.sparse_refresh':[]}.items():b.declare(code,names)
b.define('search.context.push',[],[inc('context.sp')]+[b.replace('search.context.'+n,s('context.sp'),s(n)) for n in fields],comment='Every negamax, quiescence and perft call saves all scalar node state here. Storage is allocated ahead of time (132 frames). Only replace-item operations occur during search. Moves have 512 preallocated slots per call frame; no list is indexed by chess depth. Shared history and TT tables retain learned information; child results use search.result.* and are not restored.')
b.define('search.context.pop',[],[setv(n,li('search.context.'+n,s('context.sp'))) for n in fields]+[inc('context.sp',-1)])
# The stack contains live caller state. Repeat bounds use Scratch loop frames;
# overwritten-before-use scratch (count, legal, score, drawn) is not copied twice.
b.define('search.load_move',[],[setv(n,li('search.moves.'+name,s('move_idx'))) for n,name in [('from','start'),('to','end'),('flag0','flag0'),('flag1','flag1')]])
b.define('search.check',[],[b.call('search.probe_check'),setv('in_check',V('search.probe.in_check'))])
b.define('search.try_move',[],[b.call(MAKE,s('from'),s('to'),s('flag0'),s('flag1')),b.call('search.king_probe'),setv('legal',sub(1,V('moves_generator.king_capture')))])
# The built-in dense NNUE is retained as a benchmark candidate; sparse refresh is exact.
# Input feature order matches data.evaluation_idxs_lookup and data.squares_converter.
b.define('nnue.sparse_refresh',[],[
    b.set('nnue.init_accumulator.idx0',0),
    b.repeat(96,[b.inc('nnue.init_accumulator.idx0'),b.replace('nnue.accumulator',V('nnue.init_accumulator.idx0'),li('__b0',V('nnue.init_accumulator.idx0')))]),
    b.set('nnue.sparse.square',0),
    b.repeat(64,[b.inc('nnue.sparse.square'),b.IF(NOT(eq(li('position.board',V('nnue.sparse.square')),0)),[
        b.set('nnue.sparse.feature',add(mul(li('data.evaluation_idxs_lookup',add(li('position.board',V('nnue.sparse.square')),7)),64),li('data.squares_converter',V('nnue.sparse.square')))),b.set('nnue.init_accumulator.idx0',0),
        b.repeat(96,[b.inc('nnue.init_accumulator.idx0'),b.replace('nnue.accumulator',V('nnue.init_accumulator.idx0'),add(li('nnue.accumulator',V('nnue.init_accumulator.idx0')),li('__w0',add(mul(sub(V('nnue.init_accumulator.idx0'),1),769),V('nnue.sparse.feature')))))])])]),
    b.IF(eq(V('position.turn'),1),[b.set('nnue.init_accumulator.idx0',0),b.repeat(96,[b.inc('nnue.init_accumulator.idx0'),b.replace('nnue.accumulator',V('nnue.init_accumulator.idx0'),add(li('nnue.accumulator',V('nnue.init_accumulator.idx0')),li('__w0',mul(V('nnue.init_accumulator.idx0'),769))))])])])
phase=div(V('position.game_phase'),24)
b.define('search.evaluate',[],[setv('static',mul(add(V('position.PSQT_eg_res'),mul(sub(V('position.PSQT_mg_res'),V('position.PSQT_eg_res')),phase)),V('position.turn'))),b.IF(eq(s('use_nnue'),1),[b.call('nnue.sparse_refresh'),b.call('nnue.forward'),setv('static',mul(V('nnue.output'),V('position.turn')))]),b.IF(gt(s('static'),20000),[setv('static',20000)]),b.IF(lt(s('static'),-20000),[setv('static',-20000)])])
# Limits apply at entry. Check wall time every 64 nodes, but always check an explicit stop/node budget.
b.define('search.limits',[],[b.IF(AND(gt(s('max_nodes'),0),NOT(lt(s('nodes'),s('max_nodes')))),[setv('stopped',1)]),b.IF(AND(eq(mod(s('nodes'),sub(64,mul(s('use_nnue'),60))),0),gt(s('max_time'),0)),[b.IF(NOT(lt(mul(sub(now(),s('start')),86400),s('max_time'))),[setv('stopped',1)])])])
b.define('search.draw',[],[setv('drawn',0),b.call('tools.check_current_pos_repeat_count'),b.IF(gt(V('tools.check_current_pos_repeat_count.res'),0),[setv('tt_allowed',0)]),b.IF(OR(NOT(lt(V('position.half_moves'),100)),gt(V('tools.check_current_pos_repeat_count.res'),1)),[setv('drawn',1)]),b.call('tools.check_if_draw_material'),b.IF(eq(V('tools.check_if_draw_material.res'),1),[setv('drawn',1)])])
# Capture and promotion ordering precedes quiet from/to history. No depth-indexed killers.
hidx=add(mul(eq(V('position.turn'),-1),4096),add(mul(sub(s('from'),1),64),s('to')))
b.define('search.order',[],[setv('move_idx',sub(s('base'),1)),b.repeat(s('count'),[
    inc('move_idx'),b.call('search.load_move'),setv('score',0),
    b.IF(eq(s('flag0'),1),[setv('score',sub(add(1000000,mul(li('data.material',math('abs',li('position.board',s('to')))),16)),li('data.material',math('abs',li('position.board',s('from')))))),b.IF(eq(s('flag1'),1),[setv('score',1001280)])],[b.IF(eq(s('use_history'),1),[setv('score',li('search.history',hidx))])]),
    b.IF(gt(s('flag1'),5),[inc('score',add(1200000,mul(sub(s('flag1'),4),1000)))]),
    b.IF(AND(eq(s('from'),s('tt_from')),AND(eq(s('to'),s('tt_to')),eq(s('flag1'),s('tt_flag1')))),[setv('score',10000000)]),
    b.replace('search.moves.score',s('move_idx'),sub(0,s('score')))
]),b.IF(gt(s('count'),1),[b.call('tools._quicksort %s %s',s('base'),sub(add(s('base'),s('count')),1))])])
# TT mate scores are converted between root-distance and position-distance coordinates.
b.define('search.tt_probe',[],[setv('tt_from',0),setv('tt_to',0),setv('tt_flag1',0),setv('tt_depth',-1),b.IF(AND(eq(s('tt_allowed'),1),lt(V('position.half_moves'),90)),[
    b.call('TT.probe'),b.IF(eq(V('tt.probe.res'),1),[setv('tt_from',V('tt.probe.move.start')),setv('tt_to',V('tt.probe.move.end')),setv('tt_flag1',V('tt.probe.move.flag1')),setv('tt_depth',V('tt.probe.depth')),setv('tt_flag',V('tt.probe.flag')),setv('tt_value',V('tt.probe.value')),b.IF(gt(s('tt_value'),V('_CONST.MATE_THRESHOLD')),[inc('tt_value',sub(0,s('ply')))]),b.IF(lt(s('tt_value'),sub(0,V('_CONST.MATE_THRESHOLD'))),[inc('tt_value',s('ply'))])])])])
# Normalize value AND classification windows before passing them to the retained TT store.
norm=lambda x:add(x,mul(s('ply'),sub(gt(x,V('_CONST.MATE_THRESHOLD')),lt(x,sub(0,V('_CONST.MATE_THRESHOLD'))))))
b.define('search.tt_store',[],[b.IF(AND(eq(s('tt_allowed'),1),lt(V('position.half_moves'),90)),[b.call(STORE,s('depth'),norm(s('alpha_start')),norm(s('beta_start')),norm(s('best_value')),s('best_from'),s('best_to'),s('best_flag0'),s('best_flag1'))])])
# Node entry and depth-independent child return interface.
def entry(depth,ply,alpha,beta,ext,tt):
    return [b.IF(NOT(lt(s('context.sp'),CAP-1)),[setv('stopped',1),b.set('search.result.value',0),b.ret()]),b.call('search.context.push'),setv('ply',sub(ply,1)),setv('depth',depth),setv('alpha',alpha),setv('beta',beta),setv('alpha_start',alpha),setv('beta_start',beta),setv('extension',ext),setv('tt_allowed',add(tt,0)),setv('base',add(mul(sub(s('context.sp'),1),MOVES),1)),setv('best_value',sub(0,INF)),setv('best_from',0),setv('best_to',0),setv('best_flag0',0),setv('best_flag1',0),setv('legal_count',0),setv('previous_legal',1),setv('is_pv',gt(sub(beta,alpha),1)),setv('count',0),setv('rfp',0)]
def leave():
    return [b.set('search.result.'+n,s(x)) for n,x in [('value','best_value'),('from','best_from'),('to','best_to'),('flag0','best_flag0'),('flag1','best_flag1'),('legal','previous_legal')]]+[b.call('search.context.pop')]
b.define(NEG,['PLIES_FROM_ROOT','depth','alpha','beta','total_extension','TT_activated'],entry(A('depth'),A('PLIES_FROM_ROOT'),A('alpha'),A('beta'),A('total_extension'),A('TT_activated'))+[b.call('search.node')]+leave(),comment='Public negamax: push caller context, load scalar node fields, run search, publish search.result.*, then restore caller. The implementation may return early; cleanup remains in this wrapper. Moves and scores use call-frame buffers, never depth offsets.')
b.define(Q,['PLIES_FROM_ROOT','alpha','beta'],entry(0,A('PLIES_FROM_ROOT'),A('alpha'),A('beta'),0,s('tt_allowed'))+[b.call('search.node')]+leave())
# Common initial checks for normal and quiescence nodes.
def generate():return [b.call(GEN,s('context.sp'),AND(lt(s('depth'),1),eq(s('in_check'),0))),setv('count',V('moves_generator.get_moves.moves_count_res'))]
common=[b.call('search.limits'),b.IF(eq(s('stopped'),1),[b.ret()]),inc('nodes'),
    b.call('search.king_probe'),setv('previous_legal',sub(1,V('moves_generator.king_capture'))),
    b.IF(eq(s('previous_legal'),0),[setv('best_value',INF),b.ret()]),b.call('search.draw')]
# Generate before terminal/draw/stand-pat cutoffs: checkmate takes priority over a draw claim.
# TT only cuts off at sufficient depth, and never in PV nodes: preserve a trustworthy PV.
def ttcut():return b.IF(AND(NOT(gt(sub(s('beta'),s('alpha')),1)),NOT(lt(s('tt_depth'),s('depth')))),[
    b.IF(OR(eq(s('tt_flag'),0),OR(AND(eq(s('tt_flag'),1),NOT(lt(s('tt_value'),s('beta')))),AND(eq(s('tt_flag'),2),NOT(gt(s('tt_value'),s('alpha')))))),[setv('best_flag0',V('tt.probe.move.flag0')),setv('best_value',s('tt_value')),setv('best_from',s('tt_from')),setv('best_to',s('tt_to')),setv('best_flag1',s('tt_flag1')),b.ret()])])
# draw and max-depth nodes go through quiescence's legal-move detection without recursion.
# Reverse futility pruning margin: RFP_BASE + RFP_COEF*depth^2, shared by the
# cutoff test and the loop-body score so both sites always agree.
def rfp_margin():return add(RFP_BASE,mul(RFP_COEF,mul(s('depth'),s('depth'))))
nodebody=common+[b.call('search.tt_probe'),b.IF(eq(s('drawn'),0),[ttcut()]),b.call('search.check'),
    b.IF(lt(s('alpha'),add(-MATE,s('ply'))),[setv('alpha',add(-MATE,s('ply')))]),
    b.IF(gt(s('beta'),sub(sub(MATE,s('ply')),1)),[setv('beta',sub(sub(MATE,s('ply')),1))]),
    b.IF(NOT(lt(s('alpha'),s('beta'))),[setv('best_value',s('alpha')),b.ret()]),
    b.IF(OR(lt(s('depth'),1),OR(eq(s('drawn'),1),NOT(lt(s('ply'),127)))),[b.call('search.quiescence'),b.ret()]),
    b.IF(AND(eq(s('in_check'),1),lt(s('extension'),4)),[inc('depth'),inc('extension')]),
    b.call(GEN,s('context.sp'),False),setv('count',V('moves_generator.get_moves.moves_count_res')),setv('rfp',0),
    b.IF(AND(AND(eq(s('use_pruning'),1),eq(s('use_nnue'),0)),AND(eq(s('is_pv'),0),AND(eq(s('in_check'),0),AND(lt(s('depth'),4),AND(gt(V('position.game_phase'),3),lt(math('abs',s('beta')),V('_CONST.MATE_THRESHOLD'))))))),[
        b.IF(AND(eq(li('position.moves_stack.flag0',V('_plies_from_begining')),0),lt(li('position.moves_stack.flag1',V('_plies_from_begining')),6)),[b.call('search.evaluate'),b.IF(NOT(lt(sub(s('static'),rfp_margin()),s('beta'))),[setv('rfp',1)])])]),
    b.call('search.order'),setv('move_idx',sub(s('base'),1))]
# All move loop counters and re-search state are scalars saved by each child wrapper.
child=lambda d,a,be:b.call(NEG,add(s('ply'),2),d,a,be,s('extension'),eq(s('tt_allowed'),1))
research=[child(sub(s('depth'),1),sub(-1,s('alpha')),sub(0,s('alpha'))),setv('score',sub(0,V('search.result.value'))),setv('legal',V('search.result.legal'))]
# Restore the initial engine's pseudo-move ordinal and logarithmic LMR formula.
# Checking moves and promotions still retain the correctness protections.
ordinal=sub(s('move_idx'),s('base'))
lmr_condition=AND(eq(s('use_lmr'),1),AND(NOT(lt(s('depth'),2)),AND(NOT(lt(ordinal,3)),AND(eq(s('in_check'),0),AND(eq(s('flag0'),0),lt(s('flag1'),6))))))
pvs=[setv('reduction',0),b.IF(lmr_condition,[
    # Never reduce checks or promotions; bound the reduction to leave a full ply.
    b.call('search.probe_check'),setv('gives_check',V('search.probe.in_check')),
    b.IF(eq(s('gives_check'),0),[setv('reduction',math('floor',add(LMR_BASE,div(mul(math('ln',add(ordinal,1)),math('ln',s('depth'))),LMR_DIV)))),b.IF(gt(s('reduction'),sub(s('depth'),1)),[setv('reduction',sub(s('depth'),1))])])]),
    child(sub(sub(s('depth'),1),s('reduction')),sub(-1,s('alpha')),sub(0,s('alpha'))),setv('score',sub(0,V('search.result.value'))),setv('legal',V('search.result.legal')),
    b.IF(AND(gt(s('reduction'),0),gt(s('score'),s('alpha'))),research),
    b.IF(AND(gt(s('score'),s('alpha')),lt(s('score'),s('beta'))),[child(sub(s('depth'),1),sub(0,s('beta')),sub(0,s('alpha'))),setv('score',sub(0,V('search.result.value'))),setv('legal',V('search.result.legal'))])]
def remember():return [setv('best_value',s('score'))]+[setv('best_'+n,s(n)) for n in ['from','to','flag0','flag1']]
# quiet beta-cutoff history bonus, with bounded gravity to avoid overflow/saturation.
history=[setv('history_idx',hidx),setv('bonus',mul(mul(s('depth'),s('depth')),32)),b.IF(gt(s('bonus'),2048),[setv('bonus',2048)]),b.replace('search.history',s('history_idx'),add(li('search.history',s('history_idx')),sub(s('bonus'),div(mul(li('search.history',s('history_idx')),s('bonus')),16384))))]
loopbody=[inc('move_idx'),b.call('search.load_move'),b.call(MAKE,s('from'),s('to'),s('flag0'),s('flag1')),setv('legal',1),b.IF(eq(s('legal'),1),[inc('legal_count'),b.IF(eq(s('rfp'),1),[b.call('search.king_probe'),setv('legal',sub(1,V('moves_generator.king_capture'))),setv('score',sub(s('static'),rfp_margin()))],[b.IF(eq(s('legal_count'),1),[child(sub(s('depth'),1),sub(0,s('beta')),sub(0,s('alpha'))),setv('score',sub(0,V('search.result.value'))),setv('legal',V('search.result.legal'))],pvs)])]),b.call('position.unmake_move'),b.IF(eq(s('legal'),0),[inc('legal_count',-1)]),b.IF(eq(s('stopped'),1),[b.ret()]),b.IF(eq(s('legal'),1),[
    b.IF(eq(s('rfp'),1),[setv('best_value',s('score')),b.ret()]),
    b.IF(gt(s('score'),s('best_value')),remember()),b.IF(gt(s('score'),s('alpha')),[setv('alpha',s('score'))]),b.IF(NOT(lt(s('alpha'),s('beta'))),[b.IF(AND(eq(s('use_history'),1),AND(eq(s('flag0'),0),lt(s('flag1'),6))),history),b.call('search.tt_store'),b.ret()])])]
nodebody += [b.repeat(s('count'),loopbody),b.IF(eq(s('legal_count'),0),[b.IF(eq(s('in_check'),1),[setv('best_value',add(-MATE,s('ply')))],[setv('best_value',0)])]),b.call('search.tt_store')]
b.define('search.node',[],nodebody)
# Q-search: scan until a legal move exists before accepting stand-pat (stalemate-safe).
# Once a legal quiet exists, remaining quiet moves need no make/unmake outside check.
qbody=[b.call('search.evaluate'),inc('qnodes'),setv('depth',0),
    b.IF(OR(eq(s('drawn'),1),NOT(lt(s('ply'),127))),[
        b.call('search.legal_witness'),setv('best_value',s('static')),
        b.IF(eq(s('drawn'),1),[setv('best_value',0)]),
        b.IF(eq(V('search.witness.found'),0),[b.IF(eq(s('in_check'),1),[setv('best_value',add(-MATE,s('ply')))],[setv('best_value',0)])]),b.ret()]),
    setv('best_value',-INF),
    b.IF(eq(s('in_check'),0),[b.call('search.legal_witness'),
        b.IF(eq(V('search.witness.found'),0),[setv('best_value',0),b.ret()]),
        setv('legal_count',1),setv('best_value',s('static')),
        b.IF(NOT(lt(s('static'),s('beta'))),[b.call('search.tt_store'),b.ret()]),
        b.IF(gt(s('static'),s('alpha')),[setv('alpha',s('static'))])]),
    b.IF(eq(s('count'),0),[b.call(GEN,s('context.sp'),eq(s('in_check'),0)),setv('count',V('moves_generator.get_moves.moves_count_res'))]),
    b.call('search.order'),setv('move_idx',sub(s('base'),1))]
qsearch=[b.call(Q,add(s('ply'),2),sub(0,s('beta')),sub(0,s('alpha'))),setv('score',sub(0,V('search.result.value'))),setv('legal',V('search.result.legal'))]
delta_ok=AND(AND(eq(s('use_pruning'),1),eq(s('use_nnue'),0)),AND(eq(s('in_check'),0),AND(eq(s('flag0'),1),AND(lt(s('flag1'),6),AND(gt(V('position.game_phase'),5),lt(add(add(s('static'),s('gain')),250),s('alpha')))))))
qloop=[inc('move_idx'),b.call('search.load_move'),
    b.IF(OR(eq(s('in_check'),1),OR(eq(s('flag0'),1),gt(s('flag1'),5))),[
        setv('gain',li('data.material',math('abs',li('position.board',s('to'))))),b.IF(eq(s('flag1'),1),[setv('gain',100)]),
        b.call(MAKE,s('from'),s('to'),s('flag0'),s('flag1')),setv('skip',0),
        b.IF(delta_ok,[b.call('search.probe_check'),b.IF(eq(V('search.probe.in_check'),0),[setv('skip',1)])]),
        b.IF(eq(s('skip'),0),qsearch,[setv('legal',0)]),
        b.call('position.unmake_move'),b.IF(eq(s('stopped'),1),[b.ret()]),
        b.IF(eq(s('legal'),1),[inc('legal_count'),b.IF(gt(s('score'),s('best_value')),remember()),
            b.IF(gt(s('score'),s('alpha')),[setv('alpha',s('score'))]),
            b.IF(NOT(lt(s('alpha'),s('beta'))),[b.call('search.tt_store'),b.ret()])])])]
qbody += [b.repeat(s('count'),qloop),b.IF(eq(s('legal_count'),0),[b.IF(eq(s('in_check'),1),[setv('best_value',add(-MATE,s('ply')))],[setv('best_value',0)])]),b.call('search.tt_store')]
b.define('search.quiescence',[],qbody)
# Perft uses precisely the same context and legal make/unmake path. No per-depth arrays.
b.declare('search.perft.node',[])
perftbody=entry(A('DEPTH'),A('DEPTH_FROM_ROOT'),-INF,INF,0,0)+[b.call('search.perft.node')]+leave()
b.define(PERFT,['DEPTH','DEPTH_FROM_ROOT'],perftbody)
b.define('search.perft.node',[],[setv('best_value',1),b.IF(lt(s('depth'),1),[b.ret()]),setv('best_value',0),b.call(GEN,s('context.sp'),False),setv('count',V('moves_generator.get_moves.moves_count_res'))]+[setv('move_idx',sub(s('base'),1)),b.repeat(s('count'),[inc('move_idx'),b.call('search.load_move'),b.call('search.try_move'),b.IF(eq(s('legal'),1),[b.call(PERFT,sub(s('depth'),1),add(s('ply'),2)),inc('best_value',V('search.result.value'))]),b.call('position.unmake_move')])])
# Init leaves all context stacks fixed-size and resets shared learned history on new game.
old=B['fe']['parent'];reset=[setv('context.sp',0),setv('stopped',0),setv('max_nodes',0),setv('init.i',0),b.repeat(8192,[inc('init.i'),b.replace('search.history',s('init.i'),0)])];first=b.chain(reset,old);B[reset[-1]]['next']='fe';B['fe']['parent']=reset[-1];B[old]['next']=first
# Clamp tapered game phase in promoted positions; sum can exceed the initial 24.
# Use a temporary scalar phase to avoid changing the board's actual phase count.
# Change search.evaluate's interpolation expression to clamp its own input.
# (Inserted before evaluation, the same local is recomputed at every node.)
evaldef=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']=='search.evaluate');old=B[evaldef]['next'];prefix=[setv('eval_phase',V('position.game_phase')),b.IF(gt(s('eval_phase'),24),[setv('eval_phase',24)])];B[evaldef]['next']=b.chain(prefix,evaldef);B[prefix[-1]]['next']=old;B[old]['parent']=prefix[-1]
# Only use eval_phase in the newly generated evaluation expression.
def swap_expr(k):
    v=B[k]
    if v.get('fields',{}).get('VARIABLE',[None])[0]=='position.game_phase':v['fields']['VARIABLE']=['search.eval_phase',b.variable('search.eval_phase')]
    for x in v['inputs'].values():
        if len(x)>1 and isinstance(x[1],str):swap_expr(x[1])
# The old expression was the first setter before prefix insertion.
swap_expr(old)
# Iterative driver / root fallback / PV are defined below.
exec((ROOT/'tools/driver.py').read_text())
# All generated promotion types and external DCI promotion handling are defined below.
exec((ROOT/'tools/promotions.py').read_text())
exec((ROOT/'tools/pseudo_legal.py').read_text())
b.cleanup()
# Explicitly clear monitors for removed arrays (none are required by the GUI).
P['monitors']=[m for m in P.get('monitors',[]) if m.get('id') not in old_lists]
out=pathlib.Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for info in archive.infolist():z.writestr(copy.copy(info),json.dumps(P,separators=(',',':')) if info.filename=='project.json' else archive.read(info.filename))
(ROOT/'build').mkdir(exist_ok=True);(ROOT/'build/project.json').write_text(json.dumps(P))
print(out, 'engine blocks:',len(B),'context fields:',len(fields),'frames:',CAP)
