"""Worked examples for static, extendible and linear hashing (bucket capacity 2)."""
import json, os

def static_trace(keys, m=5, cap=2):
    buckets=[[] for _ in range(m)]; trace=[]
    for k in keys:
        b=k % m; buckets[b].append(k)
        trace.append({'insert':k,'bucket':b,'buckets':[x[:] for x in buckets], 'overflow':max(0,(len(buckets[b])+cap-1)//cap-1)})
    return trace,buckets

def extendible_trace(keys, cap=2):
    gd=1; directory=[0,1]; buckets={0:{'ld':1,'keys':[]},1:{'ld':1,'keys':[]}}; next_id=2; trace=[]
    for k in keys:
        idx=k % (2**gd); bid=directory[idx]; buckets[bid]['keys'].append(k); events=[]
        while len(buckets[bid]['keys'])>cap:
            ld=buckets[bid]['ld']
            if ld==gd:
                directory=directory+directory; gd+=1
                events.append(f'directory doubled: global depth {gd}')
                idx=k % (2**gd); bid=directory[idx]
            old=buckets[bid]; new_id=next_id; next_id+=1; new_ld=old['ld']+1
            old_keys=old['keys'][:]; old['keys']=[]; old['ld']=new_ld
            buckets[new_id]={'ld':new_ld,'keys':[]}
            for i,ref in enumerate(directory):
                if ref==bid and ((i >> (new_ld-1)) & 1): directory[i]=new_id
            for val in old_keys:
                directory[val % (2**gd)]
                ref=directory[val % (2**gd)]; buckets[ref]['keys'].append(val)
            events.append(f'split bucket {bid}; local depth {new_ld}; new bucket {new_id}')
            idx=k % (2**gd); bid=directory[idx]
        state={str(i):{'bucket_id':ref,'local_depth':buckets[ref]['ld'],'keys':buckets[ref]['keys'][:]} for i,ref in enumerate(directory)}
        trace.append({'insert':k,'events':events,'global_depth':gd,'directory':state})
    return trace

def linear_trace(keys, cap=2):
    level=1; split=0; buckets={0:[],1:[]}; trace=[]
    def bucket_for(k):
        b=k%(2**level)
        if b<split: b=k%(2**(level+1))
        return b
    for k in keys:
        b=bucket_for(k); buckets.setdefault(b,[]).append(k); events=[]
        if len(buckets[b])>cap:
            s=split; new=2**level+s; buckets[new]=[]
            old=buckets[s][:]; buckets[s]=[]
            for val in old:
                nb=val%(2**(level+1))
                buckets[nb].append(val)
            events.append(f'split bucket {s} -> {s} and {new}')
            split+=1
            if split==2**level:
                level+=1; split=0; events.append(f'level advanced to {level}; split pointer reset')
        trace.append({'insert':k,'bucket_before_split':b,'events':events,'level':level,'split_pointer':split,'buckets':{str(i):v[:] for i,v in sorted(buckets.items())}})
    return trace

def main():
    os.makedirs('Results',exist_ok=True)
    st,sb=static_trace([12,7,22,17,9,14,19,24,29,34])
    et=extendible_trace([1,3,5,7,9,2,4,6,8,10,13,17,21,25])
    lt=linear_trace([2,4,6,8,1,3,5,7,9,11,13,15])
    obj={'static_hash':{'trace':st,'final_buckets':sb},'extendible_hash':et,'linear_hash':lt}
    with open('Results/hash_traces.json','w') as f: json.dump(obj,f,indent=2)
    print('STATIC HASH: m=5, bucket capacity=2, h(k)=k mod 5')
    for i,b in enumerate(sb): print(f'Bucket {i}: {b}'+(' -> overflow' if len(b)>2 else ''))
    print('\nEXTENDIBLE HASH (first 8 insertions)')
    for row in et[:8]: print(row['insert'],row['events'], 'gd=',row['global_depth'],row['directory'])
    print('\nLINEAR HASH')
    for row in lt: print(row['insert'],row['events'],'level=',row['level'],'split=',row['split_pointer'],'buckets=',row['buckets'])
    print('\nSaved Results/hash_traces.json')
if __name__=='__main__': main()
