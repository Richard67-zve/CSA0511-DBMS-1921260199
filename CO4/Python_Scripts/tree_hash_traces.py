"""Reproducible educational traces for order-4 B-tree and B+ tree, plus hash methods."""
from dataclasses import dataclass, field

@dataclass
class BNode:
    leaf: bool = True
    keys: list = field(default_factory=list)
    children: list = field(default_factory=list)

class BTree:
    def __init__(self,t=2): self.t=t; self.root=BNode()
    def split_child(self,parent,i):
        t=self.t; y=parent.children[i]; z=BNode(leaf=y.leaf)
        median=y.keys[t-1]; z.keys=y.keys[t:]; y.keys=y.keys[:t-1]
        if not y.leaf: z.children=y.children[t:]; y.children=y.children[:t]
        parent.children.insert(i+1,z); parent.keys.insert(i,median)
    def insert(self,k):
        r=self.root
        if len(r.keys)==2*self.t-1:
            s=BNode(leaf=False,children=[r]); self.root=s; self.split_child(s,0); self._insert_nonfull(s,k)
        else: self._insert_nonfull(r,k)
    def _insert_nonfull(self,x,k):
        i=len(x.keys)-1
        if x.leaf:
            x.keys.append(None)
            while i>=0 and k<x.keys[i]: x.keys[i+1]=x.keys[i]; i-=1
            x.keys[i+1]=k
        else:
            while i>=0 and k<x.keys[i]: i-=1
            i+=1
            if len(x.children[i].keys)==2*self.t-1:
                self.split_child(x,i)
                if k>x.keys[i]: i+=1
            self._insert_nonfull(x.children[i],k)
    def _get_pred(self,x,i):
        cur=x.children[i]
        while not cur.leaf: cur=cur.children[-1]
        return cur.keys[-1]
    def _get_succ(self,x,i):
        cur=x.children[i+1]
        while not cur.leaf: cur=cur.children[0]
        return cur.keys[0]
    def _merge(self,x,i):
        t=self.t; child=x.children[i]; sib=x.children[i+1]
        child.keys.append(x.keys.pop(i)); child.keys.extend(sib.keys)
        if not child.leaf: child.children.extend(sib.children)
        x.children.pop(i+1)
    def _borrow_prev(self,x,i):
        child=x.children[i]; sib=x.children[i-1]
        child.keys.insert(0,x.keys[i-1]); x.keys[i-1]=sib.keys.pop()
        if not child.leaf: child.children.insert(0,sib.children.pop())
    def _borrow_next(self,x,i):
        child=x.children[i]; sib=x.children[i+1]
        child.keys.append(x.keys[i]); x.keys[i]=sib.keys.pop(0)
        if not child.leaf: child.children.append(sib.children.pop(0))
    def _fill(self,x,i):
        t=self.t
        if i!=0 and len(x.children[i-1].keys)>=t: self._borrow_prev(x,i)
        elif i!=len(x.children)-1 and len(x.children[i+1].keys)>=t: self._borrow_next(x,i)
        else:
            if i!=len(x.children)-1: self._merge(x,i)
            else: self._merge(x,i-1)
    def _delete(self,x,k):
        t=self.t; i=0
        while i<len(x.keys) and k>x.keys[i]: i+=1
        if i<len(x.keys) and x.keys[i]==k:
            if x.leaf: x.keys.pop(i)
            elif len(x.children[i].keys)>=t:
                pred=self._get_pred(x,i); x.keys[i]=pred; self._delete(x.children[i],pred)
            elif len(x.children[i+1].keys)>=t:
                succ=self._get_succ(x,i); x.keys[i]=succ; self._delete(x.children[i+1],succ)
            else:
                self._merge(x,i); self._delete(x.children[i],k)
        else:
            if x.leaf: return False
            flag=(i==len(x.children)-1)
            if len(x.children[i].keys)<t: self._fill(x,i)
            if flag and i>len(x.keys): self._delete(x.children[i-1],k)
            else: self._delete(x.children[i],k)
        return True
    def delete(self,k):
        self._delete(self.root,k)
        if not self.root.leaf and len(self.root.keys)==0: self.root=self.root.children[0]
    def levels(self):
        out=[]; cur=[self.root]
        while cur:
            out.append(' | '.join('['+','.join(map(str,n.keys))+']' for n in cur))
            nxt=[]
            for n in cur:
                if not n.leaf: nxt.extend(n.children)
            cur=nxt
        return out


def bplus_leaf_trace():
    # Order 4 illustration: max 3 keys/leaf, min 2; internal max 4 children.
    keys=[5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85]
    leaves=[]; trace=[]
    for k in keys:
        if not leaves:
            leaves.append([k]); i=0
        else:
            starts=[b[0] for b in leaves]
            i=max(0, min(len(leaves)-1, __import__('bisect').bisect_right(starts,k)-1))
            leaves[i].append(k); leaves[i].sort()
        split=''
        if len(leaves[i])>3:
            old=leaves[i]; mid=len(old)//2; leaves[i:i+1]=[old[:mid],old[mid:]]; split=f'leaf split -> {leaves[i]} | {leaves[i+1]}'
        separators=[x[0] for x in leaves[1:]]
        trace.append((k,[x[:] for x in leaves],separators,split))
    return trace,leaves

def main():
    import os, json
    os.makedirs('Results',exist_ok=True)
    seq=[10,20,5,6,12,30,7,17,3,4,2,8,9,11,13]
    bt=BTree(t=2); btrace=[]
    for k in seq:
        bt.insert(k); btrace.append({'op':f'insert {k}','levels':bt.levels()})
    for k in [2,3,4,5]:
        before=bt.levels(); bt.delete(k); btrace.append({'op':f'delete {k}','before':before,'levels':bt.levels()})
    bptrace,leaves=bplus_leaf_trace()
    # Deletions on B+ leaf pages: merges and redistribution are explicitly recorded.
    actions=[]
    def delete_bplus(k):
        nonlocal leaves
        idx=next((i for i,b in enumerate(leaves) if b and b[0]<=k<=b[-1]), None)
        if idx is None: return {'delete':k,'status':'not found','leaves':leaves}
        leaves[idx].remove(k); event='simple delete'
        if len(leaves)>1 and len(leaves[idx])<2:
            if idx>0 and len(leaves[idx-1])>2:
                leaves[idx].insert(0,leaves[idx-1].pop()); event='redistribution from left sibling'
            elif idx+1<len(leaves) and len(leaves[idx+1])>2:
                leaves[idx].append(leaves[idx+1].pop(0)); event='redistribution from right sibling'
            elif idx>0:
                leaves[idx-1].extend(leaves[idx]); leaves.pop(idx); event='merge with left sibling'
            elif idx+1<len(leaves):
                leaves[idx].extend(leaves[idx+1]); leaves.pop(idx+1); event='merge with right sibling'
        return {'delete':k,'event':event,'leaves':[b[:] for b in leaves],'separators':[b[0] for b in leaves[1:]]}
    for k in [15,45,70,65]: actions.append(delete_bplus(k))
    with open('Results/tree_hash_traces.json','w',encoding='utf-8') as f:
        json.dump({'btree_order4':btrace,'bplus_insertions':[{'key':k,'leaves':l,'separators':s,'event':e} for k,l,s,e in bptrace], 'bplus_deletions':actions},f,indent=2)
    print('B-TREE ORDER 4 INSERTION / DELETION TRACE')
    for item in btrace: print(item['op'],'=>',' / '.join(item['levels']))
    print('\nB+ TREE LEAF INSERTION EVENTS')
    for k,l,s,e in bptrace:
        if e: print(f'{k}: {e}; separators={s}')
    print('\nB+ TREE DELETIONS')
    for a in actions: print(a)
    print('\nSaved Results/tree_hash_traces.json')
if __name__=='__main__': main()
