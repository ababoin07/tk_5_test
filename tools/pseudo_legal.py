"""Fast original-style pseudo-legal generation. No full reply-generation probes.

A king capture found while appending captures invalidates the predecessor. The
cached king status uses the original precomputed king-target capture rays, not
another traversal/generation of all enemy pieces. No king is physically captured
and undone merely to prove that an already-generated king capture takes it.
"""
# Remove the old per-ply castling-cache branch. New castling code below validates
# just the king's start/transit/destination, without generating reply move lists.
B['QS'].update(opcode='data_setvariableto',inputs={'VALUE':b.input(0)},fields={'VARIABLE':['moves_generator.legacy_castles',b.variable('moves_generator.legacy_castles')]})
# Copy the original fast king-target pseudo-capture lookup and its ray helper.
# Its scratch variables are separate from the retained diagnostic routine.
old='tools.is_square_attacked';new='moves_generator.king_target'
def variable_name(name):return new+name[len(old):] if name.startswith(old+'.') else name
def clone_value(value):
 if isinstance(value,list):
  if len(value)>=3 and value[0]==12 and isinstance(value[1],str):
   name=variable_name(value[1]);return [12,name,b.variable(name)]
  return [clone_value(x) for x in value]
 return value
for oldcode,newcode in [(ATTACK,new+' %s %s'),(old+'.slidings',new+'.slidings')]:
 d=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']==oldcode)
 ids,names=b.signatures[oldcode];b.signatures[newcode]=(ids,names)
 copied={}
 def copy_block(k):
  if k in copied:return copied[k]
  source=B[k];fields=copy.deepcopy(source['fields'])
  if 'VARIABLE' in fields:
   name=variable_name(fields['VARIABLE'][0]);fields['VARIABLE']=[name,b.variable(name)]
  mutation=copy.deepcopy(source.get('mutation'))
  if mutation and mutation.get('proccode','').startswith(old):mutation['proccode']=new+mutation['proccode'][len(old):]
  result=b.block(source['opcode'],fields=fields,mutation=mutation);copied[k]=result
  B[result]['shadow']=source.get('shadow',False)
  for name,value in source['inputs'].items():
   v=clone_value(value)
   for i,r in enumerate(value[1:],1):
    if isinstance(r,str):v[i]=copy_block(r)
   B[result]['inputs'][name]=v
  if source.get('next'):B[result]['next']=copy_block(source['next'])
  return result
 root=copy_block(d);B[root].update(topLevel=True,x=35000,y=1800+b.serial)
b.define('search.king_probe',[],[
 b.IF(eq(V('position.turn'),1),[b.call(new+' %s %s',V('position.kb_pos'),-1)],[b.call(new+' %s %s',V('position.kw_pos'),1)]),
 b.set('moves_generator.king_capture',V(new+'.attacked'))])
b.define('search.probe_check',[],[
 b.IF(eq(V('position.turn'),1),[b.call(new+' %s %s',V('position.kw_pos'),1)],[b.call(new+' %s %s',V('position.kb_pos'),-1)]),
 b.set('search.probe.in_check',V(new+'.attacked'))])
b.declare('moves_generator.castles %s',['FRAME'])
c=lambda n:V('moves_generator.castles.'+n)
cs=lambda n,x:b.set('moves_generator.castles.'+n,x)
ci=lambda n,x=1:b.inc('moves_generator.castles.'+n,x)
def both(conditions):
 result=True
 for condition in conditions:result=AND(result,condition)
 return result
body=[cs('count',V('moves_generator.get_moves.moves_count_res')),cs('king_capture',V('moves_generator.king_capture')),cs('append',add(mul(sub(A('FRAME'),1),MOVES),c('count')))]
for side,origin,transit,dest,rook,flag,right,empty in [
 (1,61,62,63,64,3,'white_castle_king_side',[62,63]),
 (1,61,60,59,57,5,'white_castle_queen_side',[60,59,58]),
 (-1,5,6,7,8,2,'black_castle_king_side',[6,7]),
 (-1,5,4,3,1,4,'black_castle_queen_side',[4,3,2])]:
 conditions=[eq(V('position.turn'),side),eq(V('position.'+right),1),eq(li('position.board',origin),side*6),eq(li('position.board',rook),side*4)]+[eq(li('position.board',x),0) for x in empty]
 steps=[b.call('search.probe_check'),cs('safe',sub(1,V('search.probe.in_check')))]
 for target,moveflag in [(transit,0),(dest,flag)]:
  steps.append(b.IF(eq(c('safe'),1),[b.call(MAKE,origin,target,0,moveflag),b.call('search.king_probe'),cs('safe',sub(1,V('moves_generator.king_capture'))),b.call('position.unmake_move')]))
 steps.append(b.IF(eq(c('safe'),1),[ci('append'),b.replace('search.moves.start',c('append'),origin),b.replace('search.moves.end',c('append'),dest),b.replace('search.moves.flag0',c('append'),0),b.replace('search.moves.flag1',c('append'),flag),ci('count')]))
 body.append(b.IF(both(conditions),steps))
body.extend([b.set('moves_generator.get_moves.moves_count_res',c('count')),b.set('moves_generator.king_capture',c('king_capture'))])
b.define('moves_generator.castles %s',['FRAME'],body)

# Instrument actual capture append sites, not an additional pass over the list.
def subtree(root):
 seen=set()
 def visit(k):
  if not k or k in seen:return
  seen.add(k);v=B[k];visit(v.get('next'))
  for value in v['inputs'].values():
   for r in value[1:]:
    if isinstance(r,str):visit(r)
 visit(root);return seen
rawcode='moves_generator.generate %s %b'
rawdef=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']==rawcode)
slidecode='moves_generator.get_moves.slidings'
slidedef=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']==slidecode)
def insert_after(k,ids):
 following=B[k].get('next');B[k]['next']=b.chain(ids,k);B[ids[-1]]['next']=following
 if following:B[following]['parent']=ids[-1]
def literal(value):
 return str(value[1][1]) if isinstance(value,list) and len(value)>1 and isinstance(value[1],list) and len(value[1])>1 else None
for k in sorted(subtree(rawdef)|subtree(slidedef)):
 v=B[k]
 if v['opcode']=='data_replaceitemoflist' and v['fields'].get('LIST',[None])[0]=='search.moves.end':
  n=v.get('next');captured=False
  for _ in range(3):
   if not n:break
   node=B[n]
   if node['opcode']=='data_replaceitemoflist' and node['fields'].get('LIST',[None])[0]=='search.moves.flag0':captured=literal(node['inputs']['ITEM'])=='1';break
   n=node.get('next')
  if captured:insert_after(k,[b.IF(eq(math('abs',li('position.board',li('search.moves.end',V('moves_generator.get_moves.adding_move_idx')))),6),[b.set('moves_generator.king_capture',1)])])
 if v['opcode']=='data_replaceitemoflist' and v['fields'].get('LIST',[None])[0]=='search.moves.flag1' and literal(v['inputs']['ITEM'])=='9':insert_after(k,[b.set('moves_generator.has_promotions',1)])
# Replace the public wrapper; cache/probe helpers never invoke this generator.
wrapper=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']==GEN)
B[wrapper]['next']=b.chain([
 b.inc('search.stats.generations'),b.set('moves_generator.king_capture',0),b.set('moves_generator.has_promotions',0),
 b.call(rawcode,A('FRAME'),A('captures_only?')),
 b.IF(eq(V('moves_generator.king_capture'),0),[
  b.IF(eq(V('moves_generator.has_promotions'),1),[b.call('moves_generator.expand_promotions %s',A('FRAME'))]),
  b.IF(NOT(A('captures_only?')),[b.call('moves_generator.castles %s',A('FRAME'))])])],wrapper)
# Quick proof of any legal move for stand-pat/draw handling. Usually the first
# pawn push suffices. Only unusual immobilized positions need full generation.
b.declare('search.witness_step %s %s %s %s',['from','to','flag0','flag1']);b.declare('search.legal_witness',[])
w=lambda n:V('search.witness.'+n)
ws=lambda n,x:b.set('search.witness.'+n,x)
wi=lambda n,x=1:b.inc('search.witness.'+n,x)
b.define('search.witness_step %s %s %s %s',['from','to','flag0','flag1'],[
 b.IF(AND(eq(s('in_check'),0),AND(NOT(eq(math('abs',li('position.board',A('from'))),6)),NOT(eq(A('flag1'),1)))),[
  b.IF(eq(V('position.turn'),1),[ws('king',V('position.kw_pos'))],[ws('king',V('position.kb_pos'))]),
  ws('dx',sub(mod(sub(A('from'),1),8),mod(sub(w('king'),1),8))),ws('dy',sub(math('floor',div(sub(A('from'),1),8)),math('floor',div(sub(w('king'),1),8)))),
  b.IF(AND(NOT(eq(w('dx'),0)),AND(NOT(eq(w('dy'),0)),NOT(eq(math('abs',w('dx')),math('abs',w('dy')))))),[ws('found',1),b.ret()])]),
 b.call(MAKE,A('from'),A('to'),A('flag0'),A('flag1')),b.call('search.king_probe'),ws('found',sub(1,V('moves_generator.king_capture'))),b.call('position.unmake_move')])
probe=lambda f,t,a=0,z=0:b.call('search.witness_step %s %s %s %s',f,t,a,z)
stop=lambda:b.IF(eq(w('found'),1),[b.ret()])
quiet_target=[ws('to',li('moves_generator.LUT_idx',w('lookup'))),b.IF(eq(li('position.board',w('to')),0),[probe(w('from'),w('to')),stop()])]
body=[ws('found',0),ws('from',48),b.IF(eq(V('position.turn'),-1),[ws('from',8)]),
 b.repeat(64,[ws('from',add(mod(w('from'),64),1)),ws('piece',li('position.board',w('from'))),
  b.IF(eq(w('piece'),V('position.turn')),[ws('to',sub(w('from'),mul(V('position.turn'),8))),
   b.IF(AND(gt(w('to'),0),lt(w('to'),65)),[b.IF(eq(li('position.board',w('to')),0),[ws('flag',0),b.IF(OR(lt(w('to'),9),gt(w('to'),56)),[ws('flag',9)]),probe(w('from'),w('to'),0,w('flag')),stop()])])]),
  b.IF(OR(eq(w('piece'),mul(V('position.turn'),2)),eq(w('piece'),mul(V('position.turn'),6))),[
   ws('offset',512),b.IF(eq(math('abs',w('piece')),6),[ws('offset',576)]),ws('lookup',li('moves_generator.LUT_LUT_end_idx',sub(add(w('from'),w('offset')),1))),
   b.repeat(sub(li('moves_generator.LUT_LUT_end_idx',add(w('from'),w('offset'))),w('lookup')),[wi('lookup')]+quiet_target)])]),
 b.inc('search.stats.witness_fallbacks'),b.call(GEN,s('context.sp'),False),setv('count',V('moves_generator.get_moves.moves_count_res')),ws('idx',sub(s('base'),1)),
 b.repeat(s('count'),[wi('idx'),probe(*[li('search.moves.'+n,w('idx')) for n in ['start','end','flag0','flag1']]),stop()])]
b.define('search.legal_witness',[],body)
