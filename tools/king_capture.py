"""King-disappearance legality, reusing pseudo-legal move generation.

No search move is checked with tools.is_square_attacked. A generated capture of
an opposing king is made temporarily; disappearance of that king marks the
previous move illegal. Frame CAP is reserved for non-recursive capture probes.
"""
# Remove the legacy castle subtree: it depends on obsolete per-ply check caches.
B['QS'].update(opcode='data_setvariableto',inputs={'VALUE':b.input(0)},fields={'VARIABLE':['moves_generator.legacy_castles',b.variable('moves_generator.legacy_castles')]})
# Existing promotion expansion already scans every generated move. Find a king
# capture there, instead of performing a separate square-attack scan.
promo_def=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']=='moves_generator.expand_promotions %s')
promo_loop=next(k for k,v in B.items() if v['opcode']=='control_repeat' and isinstance(v['inputs'].get('TIMES',[None,None])[1],str) and v['inputs']['TIMES'][1] in B and B[v['inputs']['TIMES'][1]].get('fields',{}).get('VARIABLE',[None])[0]=='moves_generator.promo.original')
substack=B[promo_loop]['inputs']['SUBSTACK'][1];after=B[substack]['next']
find_king=b.IF(eq(math('abs',li('position.board',li('search.moves.end',g('idx')))),6),[gs('king_idx',g('idx'))])
B[substack]['next']=find_king;B[find_king]['parent']=substack;B[find_king]['next']=after;B[after]['parent']=find_king
first=B[promo_def]['next'];reset=[b.set('moves_generator.king_capture',0),gs('king_idx',0)];B[promo_def]['next']=b.chain(reset,promo_def);B[reset[-1]]['next']=first;B[first]['parent']=reset[-1]
tail=first
while B[tail].get('next'):tail=B[tail]['next']
proof=[b.IF(eq(V('position.turn'),1),[gs('king_square',V('position.kb_pos')),gs('king_value',-6)],[gs('king_square',V('position.kw_pos')),gs('king_value',6)]),
 b.call(MAKE,*[li('search.moves.'+n,g('king_idx')) for n in ['start','end','flag0','flag1']]),
 b.set('moves_generator.king_capture',NOT(eq(li('position.board',g('king_square')),g('king_value')))),b.call('position.unmake_move')]
end=b.IF(gt(g('king_idx'),0),proof);B[tail]['next']=end;B[end]['parent']=tail
b.define('search.king_probe',[],[b.call(GEN,CAP,True)])
b.define('search.probe_check',[],[b.set('position.turn',sub(0,V('position.turn'))),b.call('search.king_probe'),b.set('search.probe.in_check',V('moves_generator.king_capture')),b.set('position.turn',sub(0,V('position.turn')))])
# Castling must also validate the starting square, the crossed square and the
# destination by king-disappearance probes, including a real castle make/unmake.
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
# Append castles only for full generation. Capture probes never generate castles,
# so they cannot recurse into the castle validator or disturb its scratch fields.
wrapper=next(k for k,v in B.items() if v['opcode']=='procedures_definition' and B[v['inputs']['custom_block'][1]]['mutation']['proccode']==GEN)
tail=B[wrapper]['next']
while B[tail].get('next'):tail=B[tail]['next']
castle_call=b.IF(NOT(A('captures_only?')),[b.call('moves_generator.castles %s',A('FRAME'))]);B[tail]['next']=castle_call;B[castle_call]['parent']=tail
