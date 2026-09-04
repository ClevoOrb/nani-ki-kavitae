"""Montage specific lines at high magnification to settle matra-level questions."""
import json, sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter
ROOT='/Users/pranavgangwal/Desktop/claude codes/nani-book/'
recs={r['id']:r for r in json.load(open(ROOT+'ocr/final.json'))}
def strip(pid,idx,span=2.4):
    r=recs[pid]
    im=Image.open(ROOT+'pages_raw/'+r['files'][0]).convert('L')
    a=np.asarray(im); dark=a<120
    keep=dark.mean(axis=0)<0.35
    rows=np.where((dark&keep[None,:]).sum(axis=1)>15)[0]
    cols=np.where((dark&keep[None,:]).sum(axis=0)>5)[0]
    X0,X1=max(0,cols[0]-25),min(im.width,cols[-1]+25)
    Y0,Y1=rows[0],rows[-1]; H=Y1-Y0
    lines=r['text'].split('\n')
    tot=sum(1 for l in lines if l.strip())+(1 if r.get('heading') else 0)
    before=sum(1 for l in lines[:idx] if l.strip())+(1 if r.get('heading') else 0)
    lh=H/max(tot,1)
    top=int(Y0+(before-span/2)*lh); bot=int(Y0+(before+span/2+1)*lh)
    c=im.crop((X0,max(Y0,top),X1,min(Y1,bot)))
    s=min(2.2,1950/c.width)
    c=c.resize((int(c.width*s),int(c.height*s)),Image.LANCZOS)
    a2=np.asarray(c,dtype=np.float32)
    bg=np.asarray(c.filter(ImageFilter.GaussianBlur(45)),dtype=np.float32)
    return ImageOps.autocontrast(Image.fromarray(np.clip(a2-bg+230,0,255).astype(np.uint8)),cutoff=0.4)
targets=[t.split(':') for t in sys.argv[2:]]
strips=[strip(p,int(k)) for p,k in targets]
W=max(s.width for s in strips); Hh=sum(s.height for s in strips)+24*len(strips)
canvas=Image.new('L',(W,Hh),255); y=0
for s in strips: canvas.paste(s,(0,y)); y+=s.height+24
canvas.thumbnail((2000,2000), Image.LANCZOS)
canvas.save(ROOT+f'zoomcheck/M_{sys.argv[1]}.png')
print(sys.argv[1], [f"{p} L{k}" for p,k in targets])
