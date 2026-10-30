# screen-recording-gif-tutorial

把一支螢幕操作錄影（MP4）做成可以直接分享的 **GIF 動畫教學**（同時輸出 MP4）的 Claude skill。

## 介紹短影音

55 秒直式介紹影片（用途、安裝、使用方式）：[examples/intro-short.mp4](examples/intro-short.mp4)

## 示範

以 MOSS-TTS-Nano ONNX Demo 的操作錄影製作（約 50 秒）：

![MOSS-TTS-Nano 操作教學 GIF](examples/moss-tts-nano-demo.gif)

## 成品效果

- 開頭標題字卡、每個步驟前的 STEP 字卡、結尾流程回顧字卡
- 鏡頭平滑放大到操作位置
- 重點區塊加上脈動的橘色高亮框，周圍畫面變暗（spotlight）
- 點擊位置出現紫色波紋
- 底部字幕條：步驟徽章滑入，說明文字以打字方式出現
- 等待、捲動的空檔自動加速，沒有動作的尾段剪掉

## 運作方式

1. **檢查音軌**：有語音就用 faster-whisper 轉成帶時間戳的逐字稿，依講的內容分段；音軌是靜音就改依畫面操作安排。
2. **找步驟時間與位置**：用逐幀差異找出捲動、換頁的時間點；在關鍵幀加格線讀出元件座標。
3. **寫分段表**：每段指定時間、加速倍率、步驟、字幕、高亮框、放大倍率、點擊位置。
4. **渲染**：`scripts/render.py` 逐幀合成。
5. **檢查**：抽幀拼成 contact sheet，確認框有對準、字幕沒被切掉。
6. **編碼**：ffmpeg palettegen / paletteuse 輸出 GIF，libx264 輸出 MP4。

原則：字幕只寫語音裡講的或畫面上看得到的內容，不確定的地方會在交件時說明。

## 需要的工具

- ffmpeg / ffprobe
- Python 3 + Pillow、numpy
- Noto Sans CJK 字型（使用 TC，`.ttc` index 3）
- 選用：`faster-whisper`（錄影有語音時）

## 安裝

把 `SKILL.md` 放到 Claude 的 skills 資料夾，例如：

```bash
mkdir -p ~/.claude/skills/screen-recording-gif-tutorial
cp SKILL.md ~/.claude/skills/screen-recording-gif-tutorial/
```

或在 claude.ai 的 Skills 設定中上傳。

## 單獨使用渲染程式

```bash
# 1. 抽來源幀
ffmpeg -i in.mp4 -vf fps=20 -q:v 3 src/%05d.jpg
# 2. 編輯 scripts/render.py 裡的 S（分段表）、TITLE、END 等字卡文字
python3 scripts/render.py src out
# 3. 編碼
ffmpeg -framerate 12 -i out/%05d.png -vf "palettegen=max_colors=192:stats_mode=diff" pal.png
ffmpeg -framerate 12 -i out/%05d.png -i pal.png -lavfi "paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" tutorial.gif
```

`render.py` 預設來源為 1920×1032；其他解析度請修改 `FW`、`FH` 與輸出高度 `H`。
