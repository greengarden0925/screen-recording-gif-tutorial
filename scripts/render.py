import math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC=sys.argv[1]; OUT=sys.argv[2]; os.makedirs(OUT,exist_ok=True)
FPS=12; SFPS=20; W,H=960,516; BAND=92; CH=H+BAND; FW,FH=1920,1032
MAXIDX=len(os.listdir(SRC))
FB="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"; FM="/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
def font(p,s): return ImageFont.truetype(p,s,index=3)
NAVY=(24,28,58); ACC=(255,122,0); ACC2=(124,92,255); WHITE=(255,255,255)
TITLE=[("<軟體名稱>",40,WHITE),("<主題>操作教學",32,(255,196,140))]; TITLE_SUB=["<流程一句話>"]
END=[("完成！",44,ACC),("操作流程回顧",30,WHITE)]; END_SUB=["① ...   ② ...","③ ...   ④ ..."]
S=[ # (start,end,speed,step,step_title,caption,box,zoom,clicks)
 (0,6,2.5,1,"開啟頁面","在瀏覽器開啟...",(172,56,348,100),1.45,[]),
]
def ease(x): x=max(0,min(1,x)); return x*x*(3-2*x)
def crop_for(box,z):
    if box is None or z<=1.0: return (0,0,FW,FH)
    cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2; w,h=FW/z,FH/z
    x0=min(max(cx-w/2,0),FW-w); y0=min(max(cy-h/2,0),FH-h); return (x0,y0,x0+w,y0+h)
def lerp(a,b,t): return tuple(a[i]+(b[i]-a[i])*t for i in range(len(a)))
def band(img,step,title,cap,tl):
    d=ImageDraw.Draw(img); d.rectangle([0,H,W,CH],fill=NAVY); d.rectangle([0,H,W,H+4],fill=ACC)
    sx=int(-140+160*ease(tl/0.35)); d.rounded_rectangle([sx,H+18,sx+116,H+74],14,fill=ACC)
    d.text((sx+58,H+31),"STEP",font=font(FB,13),fill=WHITE,anchor="mt")
    d.text((sx+58,H+70),str(step),font=font(FB,30),fill=WHITE,anchor="mb")
    d.text((150,H+14),title,font=font(FB,17),fill=(255,196,140))
    n=len(cap); k=int(n*ease(tl/0.7)) if tl<0.7 else n
    d.text((150,H+42),cap[:k],font=font(FM,25),fill=WHITE)
def card(lines,sub=None,t=0):
    img=Image.new("RGB",(W,CH),NAVY); d=ImageDraw.Draw(img)
    for i in range(0,CH,4):
        c=int(18*i/CH); d.line([(0,i),(W,i)],fill=(24+c,28+c,58+c*2))
    d.rectangle([0,0,int(W*ease(t/0.4)),8],fill=ACC); y=CH//2-30*len(lines)
    for i,(txt,sz,col) in enumerate(lines):
        dy=int(20*(1-ease((t-0.1*i)/0.4))); d.text((W//2,y+dy),txt,font=font(FB,sz),fill=col,anchor="mm"); y+=sz+22
    for s in (sub or []):
        d.text((W//2,y+6),s,font=font(FM,22),fill=(205,210,240),anchor="mm"); y+=36
    return img
frames=[]
def emit(img): p=f"{OUT}/{len(frames):05d}.png"; img.save(p); frames.append(p)
for i in range(int(3*FPS)): emit(card(TITLE,TITLE_SUB,i/FPS))
prev_crop=(0,0,FW,FH); prev_step=None
for (s,e,sp,step,title,cap,box,z,clicks) in S:
    if step!=prev_step:
        for i in range(int(0.9*FPS)): emit(card([(f"STEP {step}",30,ACC),(title,40,WHITE)],None,i/FPS))
    prev_step=step; target=crop_for(box,z); n=max(1,round((e-s)/sp*FPS))
    for i in range(n):
        tl=i/FPS; ts=s+tl*sp; idx=min(int(ts*SFPS)+1,MAXIDX)
        fr=Image.open(f"{SRC}/{idx:05d}.jpg").convert("RGB")
        c=lerp(prev_crop,target,ease(tl/0.6))
        img=fr.crop(tuple(int(v) for v in c)).resize((W,H),Image.LANCZOS)
        sx_,sy_=W/(c[2]-c[0]),H/(c[3]-c[1])
        tr=lambda x,y:((x-c[0])*sx_,(y-c[1])*sy_)
        if box:
            a=ease((tl-0.3)/0.4)
            if a>0:
                x0,y0=tr(box[0],box[1]); x1,y1=tr(box[2],box[3])
                dim=Image.new("RGBA",(W,H),(10,12,30,int(120*a)))
                ImageDraw.Draw(dim).rounded_rectangle([x0,y0,x1,y1],10,fill=(0,0,0,0))
                img=Image.alpha_composite(img.convert("RGBA"),dim)
                glow=Image.new("RGBA",(W,H),(0,0,0,0)); pulse=0.5+0.5*math.sin(tl*6)
                ImageDraw.Draw(glow).rounded_rectangle([x0-4,y0-4,x1+4,y1+4],12,outline=ACC+(int(160*a*pulse),),width=8)
                img=Image.alpha_composite(img,glow.filter(ImageFilter.GaussianBlur(4)))
                ImageDraw.Draw(img).rounded_rectangle([x0,y0,x1,y1],10,outline=ACC+(int(255*a),),width=3)
                img=img.convert("RGB")
        for (ct,cx,cy) in clicks:
            dt=ts-ct; L=0.9*max(sp,1)
            if 0<=dt<=L:
                p=dt/L; px,py=tr(cx,cy); ov=Image.new("RGBA",(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
                for k in (0,0.35):
                    q=p-k
                    if 0<=q<=1:
                        r=6+34*q; od.ellipse([px-r,py-r,px+r,py+r],outline=ACC2+(int(255*(1-q)),),width=4)
                od.ellipse([px-7,py-7,px+7,py+7],fill=ACC2+(int(220*(1-p)),))
                img=Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")
        canvas=Image.new("RGB",(W,CH),NAVY); canvas.paste(img,(0,0)); band(canvas,step,title,cap,tl); emit(canvas)
    prev_crop=target
for i in range(int(3.5*FPS)): emit(card(END,END_SUB,i/FPS))
print(len(frames),len(frames)/FPS)
