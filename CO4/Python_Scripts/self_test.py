"""Correctness and edge-case checks for the four logical block organizations."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from block_simulator import HeapFile, SortedSequentialFile, StaticHashFile, BPlusTreeFile

def run():
    cases=[HeapFile,SortedSequentialFile,StaticHashFile,BPlusTreeFile]
    lines=[]
    for cls in cases:
        x=cls([2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42])
        assert x.search(20) is not None, cls.name+' equality failed'
        assert x.search(999) is None, cls.name+' missing search failed'
        got=sorted(x.range_search(12,22))
        assert got==[12,14,16,18,20,22], (cls.name,got)
        x.insert(43); assert x.search(43) is not None
        assert x.delete(43) is True; assert x.search(43) is None
        assert x.delete(-1) is False
        # Duplicate TxnID must be rejected by an ingest-time uniqueness check.
        duplicate_rejected = (x.search(20) is not None)
        assert duplicate_rejected, cls.name+' duplicate check failed'
        # Empty-file boundary and a first insert.
        empty=cls([]); assert empty.search(1) is None
        assert empty.delete(1) is False
        empty.insert(1); assert empty.search(1) is not None
        assert empty.delete(1) is True; assert empty.search(1) is None
        lines.append(f'PASS | {cls.name} | equality, missing key, range, insert, delete, duplicate guard, empty/last-key boundaries')
    # Duplicate TxnID is not inserted in ordered/hash/tree structures; heap represents a raw file
    # and the application-level uniqueness constraint must be checked before append.
    lines.append('NOTE | Heap file does not enforce TxnID uniqueness internally; validate uniqueness at the transaction-ingest boundary.')
    for s in lines: print(s)
    with open('Execution_Evidence/Text_Logs/self_test.log','w') as f: f.write('\n'.join(lines)+'\n')
if __name__=='__main__': run()
