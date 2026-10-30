"""Rebuild the exact v1.3.1 archive from an unmodified v1.3.0 language archive."""
from pathlib import Path
import argparse
import hashlib
import editorial_release as editorial
from patch_tools.xp3 import read,write

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('baseline',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args()
if args.baseline.resolve()==args.output.resolve():parser.error('Output must differ from baseline')
if hashlib.sha256(args.baseline.read_bytes()).hexdigest()!=editorial.BASE_PATCH_SHA256:
 parser.error('Input is not the released v1.3.0 archive')
files=editorial.apply_native(read(args.baseline));args.output.parent.mkdir(parents=True,exist_ok=True)
write(args.output,files)
assert read(args.output)==files
assert hashlib.sha256(args.output.read_bytes()).hexdigest()==editorial.data()['patch_sha256']
print('PASS: rebuilt exact v1.3.1 archive')
