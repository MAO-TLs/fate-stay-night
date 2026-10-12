"""Strict XP3 reader/writer for the supplied unencrypted Ultimate Edition patch."""
import struct, zlib, hashlib
from pathlib import Path
MAGIC=b'XP3\r\n \n\x1a\x8bg\x01'
def chunks(data):
    pos=0
    while pos<len(data):
        tag=data[pos:pos+4]; size=struct.unpack_from('<Q',data,pos+4)[0]
        end=pos+12+size
        if end>len(data): raise ValueError('truncated chunk')
        yield tag,data[pos+12:end]
        pos=end

def read(path):
    data=Path(path).read_bytes()
    assert data[:11]==MAGIC
    off=struct.unpack_from('<Q',data,11)[0]
    seen=set(); files={}
    while True:
        assert off not in seen; seen.add(off)
        flag=data[off]; pos=off+1
        if flag&1:
            packed,raw=struct.unpack_from('<QQ',data,pos);pos+=16
            index=zlib.decompress(data[pos:pos+packed]);assert len(index)==raw
        else:
            packed=struct.unpack_from('<Q',data,pos)[0];pos+=8
            index=data[pos:pos+packed]
        for tag,entry in chunks(index):
            assert tag==b'File'
            parts=dict(chunks(entry)); info=parts[b'info']
            flags,raw,packed_size,n=struct.unpack_from('<IQQH',info)
            assert flags==0, 'encrypted entry'
            name=info[22:22+n*2].decode('utf-16le')
            assert name not in files
            out=bytearray()
            for p in range(0,len(parts[b'segm']),28):
                sf,so,sr,sp=struct.unpack_from('<IQQQ',parts[b'segm'],p)
                assert sf in (0,1)
                buf=data[so:so+sp]; buf=zlib.decompress(buf) if sf else buf
                assert len(buf)==sr;out.extend(buf)
            out=bytes(out);assert len(out)==raw
            assert zlib.adler32(out)&0xffffffff==struct.unpack('<I',parts[b'adlr'])[0],name
            files[name]=out
        if not flag&128:break
        off=struct.unpack_from('<Q',data,pos+packed)[0]
    return files

def chunk(tag,data):return tag+struct.pack('<Q',len(data))+data

def write(path,files):
    out=bytearray(MAGIC+b'\0'*8);index=bytearray()
    for name,raw in files.items():
        packed=zlib.compress(raw,9);off=len(out);out.extend(packed)
        nb=name.encode('utf-16le')
        info=struct.pack('<IQQH',0,len(raw),len(packed),len(nb)//2)+nb
        seg=struct.pack('<IQQQ',1,off,len(raw),len(packed))
        index.extend(chunk(b'File',chunk(b'info',info)+chunk(b'segm',seg)+chunk(b'adlr',struct.pack('<I',zlib.adler32(raw)&0xffffffff))))
    struct.pack_into('<Q',out,11,len(out));packed=zlib.compress(bytes(index),9)
    out.extend(b'\x01'+struct.pack('<QQ',len(packed),len(index))+packed)
    Path(path).write_bytes(out)

if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('output');a=p.parse_args()
    files=read(a.archive); root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        target=root/name
        assert target.resolve().is_relative_to(root.resolve())
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps({'entries':len(files),'extensions':{x:sum(Path(n).suffix==x for n in files) for x in sorted(set(Path(n).suffix for n in files))}},indent=2))
