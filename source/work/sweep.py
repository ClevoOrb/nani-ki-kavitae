"""Render a page as top/bottom halves at the magnification that reliably resolves matras."""
import json, sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter
ROOT='/Users/pranavgangwal/Desktop/claude codes/nani-book/'
recs={r['id']:r for r in json.load(open(ROOT+'ocr/final.json'))}
def half(pid,which,fidx=0):
    r=recs[pid]
    im=Image.open(ROOT+'pages_raw/'+r['files'][min(fidx,len(r['files'])-1)]).convert('L')
    a=np.asarray(im); dark=a<120
    keep=dark.mean(axis=0)<0.35
    rows=np.where((dark & keep[None,:]).sum(axis=1)>15)[0]
    cols=np.where((dark & keep[None,:]).sum(axis=0)>5)[0]
    X0,X1=max(0,cols[0]-25),min(im.width,cols[-1]+25)
    Y0,Y1=rows[0],rows[-1]; H=Y1-Y0
    fy=(0.0,0.56) if which=='a' else (0.50,1.0)
    c=im.crop((X0,int(Y0+H*fy[0]),X1,min(Y1+15,int(Y0+H*fy[1]))))
    s=2000/c.width
    c=c.resize((int(c.width*s),int(c.height*s)),Image.LANCZOS)
    a2=np.asarray(c,dtype=np.float32)
    bg=np.asarray(c.filter(ImageFilter.GaussianBlur(50)),dtype=np.float32)
    out=ImageOps.autocontrast(Image.fromarray(np.clip(a2-bg+230,0,255).astype(np.uint8)),cutoff=0.4)
    out.save(f'{ROOT}sweep/{pid}_{which}.png')
import os
os.makedirs(ROOT+'sweep',exist_ok=True)
for pid in sys.argv[1:]:
    for w in ('a','b'): half(pid,w)
    print(pid,'ok')
