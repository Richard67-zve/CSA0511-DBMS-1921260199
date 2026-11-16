"""Block-level file-organisation simulator for the ShopNest? No: Bank TXN CO4 case.

The simulator stores integer TxnID keys in logical 4,096-byte disk blocks.
Each key represents one fixed-length 200-byte transaction record. Counts are
logical block reads/writes, not operating-system disk I/O measurements.
"""
from __future__ import annotations
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from math import ceil, log
from typing import Iterable

BLOCK_BYTES = 4096
RECORD_BYTES = 200
RECORDS_PER_BLOCK = BLOCK_BYTES // RECORD_BYTES  # 20, unspanned
BTREE_FANOUT = 293

@dataclass
class Counters:
    reads: int = 0
    writes: int = 0
    splits: int = 0
    merges: int = 0
    overflow_blocks: int = 0

    def reset(self):
        self.reads = self.writes = self.splits = self.merges = self.overflow_blocks = 0

class HeapFile:
    name = "Heap file"
    def __init__(self, keys: Iterable[int]):
        data = list(keys)
        self.blocks = [data[i:i+RECORDS_PER_BLOCK] for i in range(0, len(data), RECORDS_PER_BLOCK)]
        self.c = Counters()
    def search(self, key: int):
        for bi, block in enumerate(self.blocks):
            self.c.reads += 1
            try:
                ri = block.index(key)
                return (bi, ri)
            except ValueError:
                pass
        return None
    def range_search(self, low: int, high: int):
        found = []
        for bi, block in enumerate(self.blocks):
            self.c.reads += 1
            found.extend(k for k in block if low <= k <= high)
        return found
    def insert(self, key: int):
        if self.blocks and len(self.blocks[-1]) < RECORDS_PER_BLOCK:
            self.blocks[-1].append(key)
            self.c.writes += 1
        else:
            self.blocks.append([key])
            self.c.writes += 1
    def delete(self, key: int):
        for block in self.blocks:
            self.c.reads += 1
            if key in block:
                block.remove(key)
                self.c.writes += 1
                return True
        return False
    @property
    def block_count(self): return len(self.blocks)

class SortedSequentialFile:
    name = "Sorted sequential + sparse index"
    def __init__(self, keys: Iterable[int]):
        data = sorted(keys)
        self.blocks = [data[i:i+RECORDS_PER_BLOCK] for i in range(0, len(data), RECORDS_PER_BLOCK)]
        self.c = Counters()
        self._refresh()
    def _refresh(self):
        self.first = [b[0] for b in self.blocks if b]
        self.index_levels = max(1, ceil(log(max(1, len(self.blocks)), BTREE_FANOUT))) if self.blocks else 1
    def _locate(self, key):
        if not self.blocks: return None
        pos = max(0, bisect_right(self.first, key)-1)
        return min(pos, len(self.blocks)-1)
    def search(self, key: int):
        if not self.blocks: self.c.reads += 1; return None
        self.c.reads += self.index_levels  # sparse-index levels
        bi = self._locate(key); self.c.reads += 1
        try: return (bi, self.blocks[bi].index(key))
        except ValueError: return None
    def range_search(self, low: int, high: int):
        if not self.blocks: self.c.reads += 1; return []
        self.c.reads += self.index_levels
        start = self._locate(low); found = []
        for block in self.blocks[start:]:
            self.c.reads += 1
            if block[0] > high: break
            found.extend(k for k in block if low <= k <= high)
        return found
    def insert(self, key: int):
        if not self.blocks:
            self.blocks = [[key]]; self.c.writes += 1; self._refresh(); return
        self.c.reads += self.index_levels
        bi = self._locate(key); block = self.blocks[bi]
        at = bisect_left(block, key)
        if at < len(block) and block[at] == key: return
        block.insert(at, key); self.c.writes += 1
        if len(block) > RECORDS_PER_BLOCK:
            mid = len(block)//2
            self.blocks[bi:bi+1] = [block[:mid], block[mid:]]
            self.c.writes += 1; self.c.splits += 1
        self._refresh()
    def delete(self, key: int):
        if not self.blocks: self.c.reads += 1; return False
        self.c.reads += self.index_levels
        bi = self._locate(key); self.c.reads += 1
        try: self.blocks[bi].remove(key)
        except ValueError: return False
        self.c.writes += 1
        if not self.blocks[bi]: self.blocks.pop(bi); self.c.writes += 1
        self._refresh(); return True
    @property
    def block_count(self): return len(self.blocks)

class StaticHashFile:
    name = "Static hash file (separate overflow pages)"
    def __init__(self, keys: Iterable[int], load_factor: float = .80):
        data = list(keys)
        self.bucket_count = max(1, ceil(len(data)/(RECORDS_PER_BLOCK*load_factor)))
        self.buckets = [[] for _ in range(self.bucket_count)]
        self.c = Counters()
        for key in data: self.buckets[key % self.bucket_count].append(key)
        self.c.overflow_blocks = sum(max(0, ceil(len(b)/RECORDS_PER_BLOCK)-1) for b in self.buckets)
    def search(self, key: int):
        bucket = self.buckets[key % self.bucket_count]
        pages = max(1, ceil(len(bucket)/RECORDS_PER_BLOCK))
        self.c.reads += pages
        try: return bucket.index(key)
        except ValueError: return None
    def range_search(self, low: int, high: int):
        found=[]
        for bucket in self.buckets:
            pages = max(1, ceil(len(bucket)/RECORDS_PER_BLOCK))
            self.c.reads += pages
            found.extend(k for k in bucket if low <= k <= high)
        return found
    def insert(self, key: int):
        bucket = self.buckets[key % self.bucket_count]
        if key in bucket: return
        before = ceil(len(bucket)/RECORDS_PER_BLOCK) if bucket else 0
        bucket.append(key); self.c.writes += 1
        after = ceil(len(bucket)/RECORDS_PER_BLOCK)
        if after > before:
            self.c.overflow_blocks += 1
    def delete(self, key: int):
        bucket = self.buckets[key % self.bucket_count]
        self.c.reads += max(1, ceil(len(bucket)/RECORDS_PER_BLOCK))
        try: bucket.remove(key)
        except ValueError: return False
        self.c.writes += 1; return True
    @property
    def block_count(self):
        return sum(max(1, ceil(len(b)/RECORDS_PER_BLOCK)) for b in self.buckets)

class BPlusTreeFile:
    """B+ tree leaf-page simulation; internal pages are represented by fanout/height.

    Leaf records are ordered by TxnID. Internal-level logical reads/writes are
    counted from the calculated fanout. Leaf pages split at 20 records; deletion
    performs leaf redistribution or merge. This is a pedagogical block model,
    not a production database index implementation.
    """
    name = "Clustered B+ tree"
    MIN_LEAF = RECORDS_PER_BLOCK // 2
    def __init__(self, keys: Iterable[int]):
        data = sorted(keys)
        self.leaves = [data[i:i+RECORDS_PER_BLOCK] for i in range(0,len(data),RECORDS_PER_BLOCK)]
        self.c = Counters(); self._refresh()
    def _refresh(self):
        self.first = [b[0] for b in self.leaves if b]
        self.height = 1 if len(self.leaves) <= 1 else 1 + ceil(log(len(self.leaves), BTREE_FANOUT))
        self.internal_pages = 0
        level = len(self.leaves)
        while level > 1:
            level = ceil(level/BTREE_FANOUT); self.internal_pages += level
    def _locate(self,key):
        return min(max(0,bisect_right(self.first,key)-1),len(self.leaves)-1)
    def search(self,key:int):
        if not self.leaves: self.c.reads += 1; return None
        bi=self._locate(key); self.c.reads += self.height
        try: return (bi,self.leaves[bi].index(key))
        except ValueError: return None
    def range_search(self,low:int,high:int):
        if not self.leaves: self.c.reads += 1; return []
        start=self._locate(low); found=[]; self.c.reads += self.height
        for block in self.leaves[start:]:
            if block[0] > high: break
            if block is not self.leaves[start]: self.c.reads += 1
            found.extend(k for k in block if low <= k <= high)
        return found
    def insert(self,key:int):
        if not self.leaves:
            self.leaves=[[key]]; self.c.writes += 1; self._refresh(); return
        bi=self._locate(key); block=self.leaves[bi]; self.c.reads += self.height
        pos=bisect_left(block,key)
        if pos < len(block) and block[pos] == key: return
        block.insert(pos,key); self.c.writes += 1
        if len(block)>RECORDS_PER_BLOCK:
            mid=len(block)//2; self.leaves[bi:bi+1]=[block[:mid],block[mid:]]
            self.c.writes += 2; self.c.splits += 1
        self._refresh()
    def delete(self,key:int):
        if not self.leaves: self.c.reads += 1; return False
        bi=self._locate(key); self.c.reads += self.height
        try: self.leaves[bi].remove(key)
        except ValueError: return False
        self.c.writes += 1
        if len(self.leaves)>1 and len(self.leaves[bi]) < self.MIN_LEAF:
            left = self.leaves[bi-1] if bi>0 else None
            right = self.leaves[bi+1] if bi+1<len(self.leaves) else None
            if left is not None and len(left)>self.MIN_LEAF:
                self.leaves[bi].insert(0,left.pop()); self.c.writes += 1
            elif right is not None and len(right)>self.MIN_LEAF:
                self.leaves[bi].append(right.pop(0)); self.c.writes += 1
            elif left is not None:
                left.extend(self.leaves[bi]); self.leaves.pop(bi); self.c.writes += 2; self.c.merges += 1
            elif right is not None:
                self.leaves[bi].extend(right); self.leaves.pop(bi+1); self.c.writes += 2; self.c.merges += 1
        if self.leaves and not self.leaves[0]: self.leaves.pop(0)
        self._refresh(); return True
    @property
    def block_count(self): return len(self.leaves)+self.internal_pages

def benchmark_one(n:int, seed:int=4211):
    import time
    probes=[min(n-1, int((i+0.5)*n/25)) for i in range(25)] if n else []
    width=min(2000,max(1,n//5))
    ranges=[]
    for j in range(5):
        lo=max(0,min(n-width, int((j+1)*n/6)))
        ranges.append((lo,lo+width-1))
    rows=[]
    classes=[HeapFile,SortedSequentialFile,StaticHashFile,BPlusTreeFile]
    for cls in classes:
        t0=time.perf_counter(); obj=cls(range(n)); build=time.perf_counter()-t0
        initial_blocks=obj.block_count
        initial_overflow=getattr(obj.c,'overflow_blocks',0)
        obj.c.reset(); t0=time.perf_counter()
        for k in probes: obj.search(k)
        eq_time=time.perf_counter()-t0
        eq_reads=obj.c.reads/len(probes) if probes else 0
        obj.c.reset(); t0=time.perf_counter()
        counts=[]
        for lo,hi in ranges: counts.append(len(obj.range_search(lo,hi)))
        range_time=time.perf_counter()-t0
        range_reads=obj.c.reads/len(ranges) if ranges else 0
        # One controlled insertion and deletion are also verified.
        obj.c.reset(); obj.insert(n+1234567); insert_reads,insert_writes,insert_splits=obj.c.reads,obj.c.writes,obj.c.splits
        obj.c.reset(); deleted=obj.delete(n+1234567); delete_reads,delete_writes,delete_merges=obj.c.reads,obj.c.writes,obj.c.merges
        rows.append({"records":n,"strategy":obj.name,"blocks":initial_blocks,"build_seconds":build,
                     "equality_avg_reads":eq_reads,"equality_seconds_25":eq_time,
                     "range_avg_reads":range_reads,"range_seconds_5":range_time,
                     "insert_reads":insert_reads,"insert_writes":insert_writes,"insert_splits":insert_splits,
                     "delete_reads":delete_reads,"delete_writes":delete_writes,"delete_merges":delete_merges,
                     "range_result_counts":";".join(map(str,counts)),"delete_verified":deleted,
                     "hash_overflow_blocks":initial_overflow if cls is StaticHashFile else 0,
                     "tree_height":getattr(obj,"height",0) if cls is BPlusTreeFile else 0})
        del obj
    return rows

def main():
    import argparse, csv, os, json, time
    p=argparse.ArgumentParser(); p.add_argument('--sizes',default='1000,10000,100000,1000000'); p.add_argument('--out',default='Results/benchmark.csv')
    a=p.parse_args(); sizes=[int(x) for x in a.sizes.split(',')]
    allrows=[]
    for n in sizes:
        print(f'Benchmarking {n:,} records...',flush=True)
        allrows.extend(benchmark_one(n))
    os.makedirs(os.path.dirname(a.out) or '.',exist_ok=True)
    with open(a.out,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0])); w.writeheader(); w.writerows(allrows)
    print('\nSUMMARY')
    for r in allrows:
        print(f"{r['records']:>9,} | {r['strategy']:<37} | blocks={r['blocks']:>7,} | eq_reads={r['equality_avg_reads']:.2f} | range_reads={r['range_avg_reads']:.2f} | build={r['build_seconds']:.4f}s")
    print(f'\nWrote {a.out}')
if __name__=='__main__': main()
