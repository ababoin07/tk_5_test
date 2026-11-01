"""Small Scratch 3 block builder; generated expressions are never shared by two parents."""
import copy,json
class Expr:
    def __init__(self,op,inputs=None,fields=None):self.op,self.inputs,self.fields=op,inputs or {},fields or {}
def V(n):return Expr('data_variable',fields={'VARIABLE':[n,None]})
def A(n):return Expr('argument_reporter_string_number',fields={'VALUE':[n,None]})
def binary(op,a,b):
    names=('OPERAND1','OPERAND2') if op in ('equals','lt','gt','and','or') else ('NUM1','NUM2')
    return Expr('operator_'+op,dict(zip(names,(a,b))))
def add(a,b):return binary('add',a,b)
def sub(a,b):return binary('subtract',a,b)
def mul(a,b):return binary('multiply',a,b)
def div(a,b):return binary('divide',a,b)
def mod(a,b):return binary('mod',a,b)
def eq(a,b):return binary('equals',a,b)
def lt(a,b):return binary('lt',a,b)
def gt(a,b):return binary('gt',a,b)
def AND(a,b):return binary('and',a,b)
def OR(a,b):return binary('or',a,b)
def NOT(a):return Expr('operator_not',{'OPERAND':a})
def math(op,x):return Expr('operator_mathop',{'NUM':x},{'OPERATOR':[op,None]})
def join(a,b):return Expr('operator_join',{'STRING1':a,'STRING2':b})
def letter(i,s):return Expr('operator_letter_of',{'LETTER':i,'STRING':s})
def now():return Expr('sensing_dayssince2000')
class Builder:
    def __init__(self,project,target):
        self.project,self.target=project,target;self.B=target['blocks'];self.serial=0
        self.signatures={b['mutation']['proccode']:(json.loads(b['mutation']['argumentids']),json.loads(b['mutation'].get('argumentnames','[]'))) for b in self.B.values() if b['opcode']=='procedures_prototype'}
    def uid(self):self.serial+=1;return 'v54_'+str(self.serial)
    def variable(self,n):
        for t in (self.target,self.project['targets'][0]):
            for k,v in t['variables'].items():
                if v[0]==n:return k
        k='v54_var_'+n;self.target['variables'][k]=[n,0];return k
    def listid(self,n):
        for t in (self.target,self.project['targets'][0]):
            for k,v in t['lists'].items():
                if v[0]==n:return k
        raise KeyError(n)
    def newlist(self,n,length):
        k='v54_list_'+n;self.target['lists'][k]=[n,[0]*length];return k
    def input(self,x):
        if isinstance(x,Expr):
            fields=copy.deepcopy(x.fields)
            if 'VARIABLE' in fields:fields['VARIABLE'][1]=self.variable(fields['VARIABLE'][0])
            if 'LIST' in fields:fields['LIST'][1]=self.listid(fields['LIST'][0])
            return [2,self.block(x.op,{k:self.input(v) for k,v in x.inputs.items()},fields)]
        if isinstance(x,bool):return self.input(eq(1,int(x)))
        return [1,[10,str(x)]]
    def block(self,op,inputs=None,fields=None,mutation=None):
        k=self.uid();self.B[k]={'opcode':op,'next':None,'parent':None,'inputs':inputs or {},'fields':fields or {},'shadow':False,'topLevel':False}
        if mutation is not None:self.B[k]['mutation']=mutation
        return k
    def cmd(self,op,inputs=None,fields=None):return self.block(op,{k:self.input(v) for k,v in (inputs or {}).items()},fields)
    def broadcast(self,name,wait=False):
        # Broadcast menus are literal shadow inputs, never executable reporter blocks.
        broadcasts=self.project['targets'][0]['broadcasts']
        id=next(k for k,v in broadcasts.items() if v==name)
        return self.block('event_broadcastandwait' if wait else 'event_broadcast',
                          {'BROADCAST_INPUT':[1,[11,name,id]]})
    def set(self,n,x):return self.cmd('data_setvariableto',{'VALUE':x},{'VARIABLE':[n,self.variable(n)]})
    def inc(self,n,x=1):return self.cmd('data_changevariableby',{'VALUE':x},{'VARIABLE':[n,self.variable(n)]})
    def item(self,n,i):return Expr('data_itemoflist',{'INDEX':i},{'LIST':[n,None]})
    def replace(self,n,i,x):return self.cmd('data_replaceitemoflist',{'INDEX':i,'ITEM':x},{'LIST':[n,self.listid(n)]})
    def append(self,n,x):return self.cmd('data_addtolist',{'ITEM':x},{'LIST':[n,self.listid(n)]})
    def chain(self,ids,parent=None):
        ids=[x for x in ids if x is not None]
        for i,k in enumerate(ids):self.B[k]['parent']=ids[i-1] if i else parent;self.B[k]['next']=ids[i+1] if i+1<len(ids) else None
        return ids[0] if ids else None
    def IF(self,condition,body,other=None):
        k=self.cmd('control_if_else' if other is not None else 'control_if',{'CONDITION':condition});self.B[k]['inputs']['SUBSTACK']=[2,self.chain(body,k)]
        if other is not None:self.B[k]['inputs']['SUBSTACK2']=[2,self.chain(other,k)]
        return k
    def repeat(self,n,body):
        k=self.cmd('control_repeat',{'TIMES':n});self.B[k]['inputs']['SUBSTACK']=[2,self.chain(body,k)];return k
    def until(self,c,body):
        k=self.cmd('control_repeat_until',{'CONDITION':c});self.B[k]['inputs']['SUBSTACK']=[2,self.chain(body,k)];return k
    def ret(self):return self.cmd('control_stop',fields={'STOP_OPTION':['this script',None]})
    def declare(self,code,names):
        if code not in self.signatures:self.signatures[code]=(['v54_arg_'+code+'_'+str(i) for i in range(len(names))],names)
    def call(self,code,*args):
        ids,names=self.signatures[code];assert len(ids)==len(args),(code,args)
        return self.block('procedures_call',dict(zip(ids,map(self.input,args))),mutation={'tagName':'mutation','children':[],'proccode':code,'argumentids':json.dumps(ids),'warp':'true'})
    def define(self,code,names,body,warp=True,comment=None):
        self.declare(code,names);ids,_=self.signatures[code];m={'tagName':'mutation','children':[],'proccode':code,'argumentids':json.dumps(ids),'argumentnames':json.dumps(names),'argumentdefaults':json.dumps(['']*len(names)),'warp':str(warp).lower()}
        p=self.block('procedures_prototype',mutation=m);self.B[p]['shadow']=True
        types=[x for x in code.split() if x in ('%s','%b')]
        for id,n,typ in zip(ids,names,types):
            r=self.block('argument_reporter_boolean' if typ=='%b' else 'argument_reporter_string_number',fields={'VALUE':[n,None]});self.B[r]['shadow']=True;self.B[p]['inputs'][id]=[1,r]
        d=self.block('procedures_definition',{'custom_block':[1,p]});self.B[d].update(topLevel=True,x=34000,y=2000+self.serial*2);self.B[d]['next']=self.chain(body,d)
        if comment:
            c=self.uid();self.B[d]['comment']=c;self.target['comments'][c]={'blockId':d,'x':34500,'y':self.B[d]['y'],'width':480,'height':240,'minimized':False,'text':comment}
        return d
    def cleanup(self):
        seen=set()
        def visit(k,parent=None):
            if k is None:return
            if k not in self.B:raise ValueError(k)
            if k in seen:raise ValueError('shared/cyclic block '+k)
            seen.add(k);b=self.B[k];b['parent']=parent
            visit(b.get('next'),k)
            for v in b['inputs'].values():
                for r in v[1:]:
                    if isinstance(r,str):visit(r,k)
        for k,b in list(self.B.items()):
            if b.get('topLevel'):visit(k)
        for k in list(self.B):
            if k not in seen:del self.B[k]
        for k in list(self.target.get('comments',{})):
            if self.target['comments'][k].get('blockId') not in seen:del self.target['comments'][k]
