#!/usr/bin/env python3
"""Test that code values and pixel layout of HDR10 source patterns are sane."""
import importlib.util
import pathlib
import struct
import sys
root = pathlib.Path(__file__).resolve().parents[1]
file = root / 'app/hdr10_patterns.py'
spec=importlib.util.spec_from_file_location('patterns', file)
patterns=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=patterns
spec.loader.exec_module(patterns)
assert abs(patterns.pq_encode(10000)-1.0) < 1e-9
assert abs(patterns.pq_encode(0)) < 1e-6
assert patterns.limited10(0)==64
assert patterns.limited10(10000)==940
assert all(patterns.limited10(x)<patterns.limited10(y) for x,y in zip(patterns.STEPS,patterns.STEPS[1:]))
f=patterns.make_frame(256,256,1000)
assert len(f)==256*256*3
# center Y sample should be 1000-nit signal, corner black
index_center=128*256+128
assert struct.unpack_from('<H',f,index_center*2)[0]==patterns.limited10(1000)
assert struct.unpack_from('<H',f,0)[0]==64
# neutral Cb/Cr planes exact midpoint
assert all(x==512 for x in struct.unpack_from('<100H',f,256*256*2))
print('PQ ST2084 + limited-range 10-bit source signals: OK')
