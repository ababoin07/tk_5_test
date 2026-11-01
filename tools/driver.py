"""Executed by build.py with its block-builder namespace."""
for code,names in {'search.fallback.node %s':['wanted'],'search.run_iteration':[],'search.pv.step':[]}.items():b.declare(code,names)
# On timeout keep the last COMPLETED iteration. Before one completes, keep a legal fallback.
rootcopy=[b.set('search.root.'+n,s(n)) for n in ['from','to','flag0','flag1']]
b.define('search.root_fallback %s',['wanted'],[b.call('search.context.push'),setv('base',add(mul(sub(s('context.sp'),1),MOVES),1)),b.call('search.fallback.node %s',A('wanted')),b.call('search.context.pop')])
fallback=[b.set('search.root.'+n,0) for n in ['from','to','flag0','flag1']]+[setv('book.found',0)]+generate()+[setv('move_idx',sub(s('base'),1)),b.repeat(s('count'),[
    inc('move_idx'),b.call('search.load_move'),b.call('search.try_move'),b.call('position.unmake_move'),b.IF(eq(s('legal'),1),[
        b.IF(eq(V('search.root.from'),0),[b.set('search.root.'+n,s(n)) for n in ['from','to','flag0','flag1']]),
        b.IF(eq(A('wanted'),''),[b.ret()]),b.call(NOTATION,s('from'),s('to'),s('flag0'),s('flag1')),
        b.IF(eq(V('tools.get_uci_notation.res'),A('wanted')),[b.set('search.root.'+n,s(n)) for n in ['from','to','flag0','flag1']]+[setv('book.found',1),b.ret()])
    ])])]
b.define('search.fallback.node %s',['wanted'],fallback)
# Publish the chosen root move directly, independent of TT replacement and timeout state.
b.define('search.emit',[],[
    b.IF(eq(V('search.root.from'),0),[setv('root.move','0000')],[
        b.call(NOTATION,*[V('search.root.'+n) for n in ['from','to','flag0','flag1']]),
        setv('root.move',V('tools.get_uci_notation.res'))]),
    b.append('_dci',join('m',s('root.move'))),
    b.broadcast('dci message',wait=True)])

# A progressively widening aspiration window; retry both fail-high and fail-low.
lo=lambda:sub(s('root.score'),s('asp.window'));hi=lambda:add(s('root.score'),s('asp.window'))
b.define('search.run_iteration',[],[
    setv('asp.window',32),b.IF(lt(V('iterative_deepening.depth'),4),[setv('asp.window',INF*2)]),setv('asp.done',0),
    b.until(OR(eq(s('asp.done'),1),eq(s('stopped'),1)),[
        setv('asp.alpha',lo()),setv('asp.beta',hi()),b.IF(gt(s('asp.window'),4000),[setv('asp.alpha',-INF),setv('asp.beta',INF)]),
        b.call(NEG,1,V('iterative_deepening.depth'),s('asp.alpha'),s('asp.beta'),0,True),
        b.IF(AND(gt(V('search.result.value'),s('asp.alpha')),lt(V('search.result.value'),s('asp.beta'))),[setv('asp.done',1)],[setv('asp.window',mul(s('asp.window'),2))])])])
# Safe PV extraction: each TT move must match a generated LEGAL move. All temporary moves undo.
pvstep=[setv('pv.found',0)]+generate()+[setv('move_idx',sub(s('base'),1)),b.repeat(s('count'),[
    inc('move_idx'),b.call('search.load_move'),b.IF(AND(eq(s('from'),s('pv.from')),AND(eq(s('to'),s('pv.to')),eq(s('flag1'),s('pv.flag1')))),[
        b.call('search.try_move'),b.IF(eq(s('legal'),1),[b.call(NOTATION,s('from'),s('to'),s('flag0'),s('flag1')),setv('build_pv.res',join(s('build_pv.res'),join(V('tools.get_uci_notation.res'),' '))),setv('pv.found',1),b.ret()]),b.call('position.unmake_move')])])]
b.define('search.pv.step',[],pvstep)
b.define('search.build_pv',[],[b.call('search.context.push'),setv('base',add(mul(sub(s('context.sp'),1),MOVES),1)),setv('build_pv.res',''),setv('pv.count',0),setv('pv.break',0),setv('pv.from',V('search.root.from')),setv('pv.to',V('search.root.to')),setv('pv.flag1',V('search.root.flag1')),
    b.repeat(s('completed_depth'),[b.IF(eq(s('pv.break'),0),[b.call('search.pv.step'),b.IF(eq(s('pv.found'),1),[inc('pv.count'),b.call('TT.probe'),b.IF(AND(eq(V('tt.probe.res'),1),eq(V('tt.probe.flag'),0)),[setv('pv.from',V('tt.probe.move.start')),setv('pv.to',V('tt.probe.move.end')),setv('pv.flag1',V('tt.probe.move.flag1'))],[setv('pv.break',1)])],[setv('pv.break',1)])])]),b.repeat(s('pv.count'),[b.call('position.unmake_move')]),b.call('search.context.pop')])
# DCI evaluation is white-relative. Search/aspiration scores remain side-to-move relative.
# Match the GUI's existing "depth pv" and centipawn-or-M strings.
for code,names in {'search.report':[]}.items():b.declare(code,names)
cp=mul(s('root.score'),V('position.turn'))
# Positive M distance in moves, negative distance for the losing side.
matemoves=math('ceiling',div(sub(MATE,math('abs',s('root.score'))),2))
b.define('search.report',[],[setv('evaluation',cp),b.set('_dci evaluation',div(s('evaluation'),100)),setv('report.score',join('cp ',s('evaluation'))),b.IF(gt(math('abs',s('root.score')),V('_CONST.MATE_THRESHOLD')),[setv('report.mate',matemoves),b.IF(lt(s('evaluation'),0),[setv('report.mate',sub(0,s('report.mate')))]),b.set('_dci evaluation',join('M',s('report.mate'))),setv('report.score',join('mate ',s('report.mate')))]),
    b.set('_dci pv',join(join(s('completed_depth'),' '),s('build_pv.res'))),
    setv('report.elapsed',mul(sub(now(),s('start')),86400)),b.IF(lt(s('report.elapsed'),0.001),[setv('report.elapsed',0.001)]),
    b.append('_CONSOLE',join(join(join(join('info depth ',s('completed_depth')),join(' seldepth ',s('sel_depth'))),join(' score ',s('report.score'))),join(join(join(' nodes ',s('nodes')),join(' nps ',math('floor',div(s('nodes'),s('report.elapsed'))))),join(' pv ',s('build_pv.res'))))),b.append('_dci',li('_CONSOLE',Expr('data_lengthoflist',fields={'LIST':['_CONSOLE',None]}))),
    b.broadcast('gui refresh stats')])
b.define(ITER,['max_time','max_depth'],[
    setv('context.sp',0),setv('nodes',0),setv('qnodes',0),setv('stopped',0),setv('start',now()),setv('max_time',A('max_time')),setv('max_nodes',V('_dci max nodes')),b.IF(AND(NOT(gt(s('max_time'),0)),AND(NOT(gt(A('max_depth'),0)),NOT(gt(s('max_nodes'),0)))),[setv('max_time',1)]),setv('completed_depth',0),setv('root.score',0),setv('sel_depth',0),setv('book.move',''),
    b.IF(AND(eq(s('use_book'),1),Expr('data_listcontainsitem',{'ITEM':add(V('position.positionnal_hash'),V('position.datas_hash'))},{'LIST':['_OPENING_BOOK',None]})),[
        setv('book.move',li('_OPENING_BOOK',add(Expr('data_itemnumoflist',{'ITEM':add(V('position.positionnal_hash'),V('position.datas_hash'))},{'LIST':['_OPENING_BOOK',None]}),1)))
    ]),b.call('search.root_fallback %s',s('book.move')),b.IF(OR(eq(s('book.found'),1),eq(V('search.root.from'),0)),[b.call('search.emit'),b.ret()]),
    b.set('iterative_deepening.depth',0),setv('depth_limit',A('max_depth')),b.IF(OR(lt(s('depth_limit'),1),gt(s('depth_limit'),64)),[setv('depth_limit',64)]),
    b.repeat(s('depth_limit'),[
        b.IF(eq(s('stopped'),0),[b.inc('iterative_deepening.depth'),b.inc('tt.age'),b.call('search.run_iteration'),b.IF(eq(s('stopped'),0),[
            setv('completed_depth',V('iterative_deepening.depth')),setv('root.score',V('search.result.value')),
            *[b.set('search.root.'+n,V('search.result.'+n)) for n in ['from','to','flag0','flag1']],
            b.call('search.build_pv'),b.call('search.report'),b.IF(gt(math('abs',s('root.score')),V('_CONST.MATE_THRESHOLD')),[setv('stopped',1)])])])]),b.call('search.emit')],warp=False)
# Track maximum selective depth without a depth-indexed array.
node_def=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']=='search.node');first=B[node_def]['next'];d=b.IF(gt(add(s('ply'),1),s('sel_depth')),[setv('sel_depth',add(s('ply'),1))]);B[node_def]['next']=d;B[d]['parent']=node_def;B[d]['next']=first;B[first]['parent']=d
