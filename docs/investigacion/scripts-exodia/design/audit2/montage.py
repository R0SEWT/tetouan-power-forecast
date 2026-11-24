import sys,glob,os
from PIL import Image
src,out=sys.argv[1],sys.argv[2]; files=sorted([f for f in glob.glob(src+'/*.png')+glob.glob(src+'/*.jpg') if not os.path.basename(f).startswith('m_')],key=lambda f:int(''.join(c for c in os.path.basename(f) if c.isdigit()) or 0))
per=int(sys.argv[3]) if len(sys.argv)>3 else 4
for k in range(0,len(files),per):
    ims=[Image.open(f).convert('RGB') for f in files[k:k+per]]
    W=900; rs=[im.resize((W,int(im.height*W/im.width))) for im in ims]
    H=sum(r.height for r in rs)+30*len(rs)
    m=Image.new('RGB',(W,H),'white'); y=0
    from PIL import ImageDraw
    d=ImageDraw.Draw(m)
    for f,r in zip(files[k:k+per],rs):
        d.text((5,y+5),os.path.basename(f),fill='red'); y+=30; m.paste(r,(0,y)); y+=r.height
    m.save(f'{out}_{k//per}.png'); print(f'{out}_{k//per}.png',[os.path.basename(f) for f in files[k:k+per]])
