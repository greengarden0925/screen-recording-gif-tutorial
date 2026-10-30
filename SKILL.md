---
name: "screen-recording-gif-tutorial"
description: "把螢幕錄影（MP4）做成 GIF 動畫教學：依語音或畫面操作加上放大、高亮框、點擊波紋、步驟字幕與字卡。使用者給錄影並說要做 GIF 教學、操作教學動畫時使用。"
---

# 螢幕錄影 → GIF 動畫教學

把一支操作錄影做成可直接分享的 GIF 教學（並附同內容 MP4）。成品包含：開頭標題字卡、每步驟 STEP 字卡、鏡頭平滑放大到操作位置、脈動橘色高亮框加周圍變暗（spotlight）、點擊位置紫色波紋、底部字幕條（步驟徽章滑入＋說明文字打字效果）、結尾流程回顧字卡。空檔加速、無動作的尾段剪掉。

## 鐵則
- 嚴禁編撰：說明文字只寫語音裡講的或畫面上確實看得到的內容。看不出來的（例如檔案格式、是否真的按下按鈕）不要寫死，交件時向使用者說明不確定處。
- 字幕一律繁體中文，用 Noto Sans CJK 的 TC（ttc index=3）。
- 原始上傳檔不改，複製到工作目錄處理。

## 流程

### 1. 檢查影片與音軌
```bash
mkdir -p work && cp "<上傳檔>" work/in.mp4 && cd work
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact in.mp4
ffmpeg -v error -i in.mp4 -ac 1 -ar 16000 a.wav
ffmpeg -i a.wav -af volumedetect -f null - 2>&1 | grep -E "mean|max"
```
- 若 max_volume 接近 -91 dB → 音軌是靜音，改依畫面操作安排，並在一開始告訴使用者。
- 若有聲音 → `pip install --break-system-packages faster-whisper`，用 small/medium 模型、language="zh" 轉出帶時間戳的逐字稿，作為字幕與分段依據（簡體輸出要轉繁體）。

### 2. 看懂畫面、找出分段點
- 每 3 秒抽一張縮圖拼成 contact sheet（每張 6 格）用 Read 看，掌握整體流程。
- 用逐幀差異找捲動/換頁時間點（差異大＝版面變了，高亮框座標要換）：
```python
# ffmpeg -i in.mp4 -vf fps=2,scale=480:-1,format=gray s1/%03d.png
import numpy as np,glob; from PIL import Image
fs=sorted(glob.glob('s1/*.png')); prev=None
for i,f in enumerate(fs):
    a=np.asarray(Image.open(f),dtype=float)[25:,:]
    if prev is not None and np.abs(a-prev).mean()>0.3: print(f'{i/2:.1f}s', round(np.abs(a-prev).mean(),2))
    prev=a
```
- 在每個穩定版面各抽一張關鍵幀（960 寬），畫上每 50px 的格線再拼圖 Read，讀出要框的元件座標（×2 換回原解析度）。
- 選單、彈出視窗等短暫元素：對該區域算平均亮度，逐 0.5 秒找出出現時間，再裁原解析度局部圖確認精確位置。
- 點擊時間：游標停在按鈕上＋下一刻畫面有反應（播放鍵變暫停、選單出現）。

### 3. 定義分段表
每段一列：`(起秒, 迄秒, 加速倍率, 步驟編號, 步驟標題, 說明字幕, 高亮框(原解析度 x0,y0,x1,y1) 或 None, 放大倍率, 點擊[(秒,x,y)])`
- 有操作的段落 1–1.5 倍；等待、捲動空檔 2.5–5 倍；無意義尾段直接不放。
- 放大倍率 1.35–1.6；捲動中或全頁說明的段落用 None＋1.0。
- 字幕長度在 960 寬、25px 字下約 28 個全形字以內，超過會被切掉，要縮短。
- 同一步驟可拆多段（換框、換字幕），步驟編號變了才插 STEP 字卡。

### 4. 渲染
先把來源抽成 20fps JPG（`ffmpeg -i in.mp4 -t <最後用到的秒數> -vf fps=20 -q:v 3 src/%05d.jpg`），再用下面腳本（存到工作目錄外的 scripts/render.py，修改 S、字卡文字、總幀數上限後執行 `python3 scripts/render.py src out`）。來源若不是 1920×1032，改 FW/FH 與輸出 H（保持比例）。

```python
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
```

### 5. 檢查
- 抽 12 張輸出幀拼成 contact sheet 用 Read 看：框有沒有對準、字幕有沒有被切掉、放大後是否超出畫面。有問題就改分段表重跑（渲染約 30 秒）。

### 6. 編碼與交付
```bash
ffmpeg -v error -y -framerate 12 -i out/%05d.png -vf "palettegen=max_colors=192:stats_mode=diff" pal.png
ffmpeg -v error -y -framerate 12 -i out/%05d.png -i pal.png -lavfi "paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" <名稱>_教學.gif
ffmpeg -v error -y -framerate 12 -i out/%05d.png -c:v libx264 -pix_fmt yuv420p -crf 20 -preset veryfast <名稱>_教學.mp4
```
- GIF 約 50 秒時大小 15 MB 左右；太大就把 FPS 降到 10、max_colors 降到 128，或把輸出寬度縮到 800。
- 用 SendUserFile 一起送 GIF 與 MP4。回覆中說明：步驟架構、動畫效果、加速/剪掉的部分，以及任何不確定的標示（例如音軌靜音、無法確認是否真的點擊）。如果沒有語音，主動提議：給旁白稿或錄音就能重新對齊。