# Photo Auto Beautify · 本地免费批量图片美化

[English](README.md) | **简体中文**

> 不订阅、不上传、不逐张修图：一条命令把整批 RAW/JPG/HEIC 出成可交付成片。

纯命令行照片流水线 skill：正常片自动美化，明显问题生成修正候选并询问，疑似问题只给建议。

## 能力

- 自动分诊：正常 / 明显问题 / 疑似问题，整图模糊单独提示；
- 场景感知：人像、夜景、高调、风景、通用；
- 三档强度：默认中档，可切最低 / 最高；
- 人像：皮肤平滑、眼白/牙齿轻微提亮，不瘦脸、不改五官；
- 风格：黑白、轻/强去雾、夜景、食物，配置可扩展；
- 选片：模糊、曝光异常、近似重复，只报告不删图；
- 多格式输入，统一输出 JPEG；
- 原图保护、统一命名、修正候选确认、清理中间产物。

## 支持的格式

RAW（RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW 等）、JPEG、PNG、TIFF、
WebP、AVIF、HEIC/HEIF、JPEG XL、BMP、GIF（首帧）；输出统一 JPEG。

HEIC 需要 `pillow-heif`；JXL 需要 `ffmpeg`（libjxl）。

## 默认规则

| 分类 | 处理 |
| --- | --- |
| 正常 | 默认中档美化；用户要求时用 `min` / `max` |
| 明显问题 | 保留原图，生成 `<原名>-fixed.jpg` 候选，再询问 |
| 疑似问题 | 只给建议，不生成文件 |
| 明显但无法修复 | 整图模糊等只提示重拍/检查对焦 |

命名：

- RAW 正常片 → `<原名>.jpg`
- 其他格式正常片 → `<原名>-beauty.jpg`
- 明显问题 → `<原名>-fixed.jpg`
- 最终只保留原图、美化文件、修正候选；预览/暂存清理

## 安装

```bash
npx skills add kingforder/Photo-Auto-Beautify
```

或复制 `skills/photo-auto-beautify/` 到 agent 的 skills 目录。

## 使用

```powershell
$Skill = ".\skills\photo-auto-beautify"
$env:PYTHONPATH = "..\face-deps"

python "$Skill\scripts\photo-pipeline.py" `
  --input "C:\photos" --output-dir "C:\photos" `
  --strength medium `
  --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

- `--strength min|medium|max`：默认 medium；
- `--dry-run`：只输出分诊计划；
- `--temp-dir`：受限环境指定可写临时目录；
- 跑完先看报告，再确认 `*-fixed.jpg` 是否保留。

Linux / WSL：

```bash
cd skills/photo-auto-beautify
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-rt.sh
python3 scripts/photo-pipeline.py \
  --input "$HOME/photos" --output-dir "$HOME/photos" \
  --strength medium \
  --report "$HOME/photos/pipeline-report.md"
```

Linux 需要当前 Python 环境已有 Pillow/NumPy/OpenCV/pillow-heif；建议用 venv
或发行版包。未安装 RAWmakase 时，RAW 预览会自动回退到 RawTherapee。

## 覆盖原图（危险，默认关闭）

默认绝不覆盖原图。只有用户明确要求并接受不可逆后果时，才加
`--overwrite-originals`：

- 仅普通 JPG/JPEG 正常片写回原路径；
- RAW 仍保留原片，只生成同名 `.jpg`；
- PNG/WebP/HEIC/JXL 仍生成 `-beauty.jpg`，不改原文件；
- `*-fixed.jpg` 仍是待确认候选，不自动覆盖；
- 建议先备份，不要默认开启。

## 依赖

- Windows 10/11，或 Linux / WSL2
- Python 3.10+，Pillow、NumPy、OpenCV
- `pillow-heif`（HEIC/HEIF），`ffmpeg`（JPEG XL）
- RawTherapee 5.13：Windows 用 `scripts/setup-rt.ps1`，Linux 用 `scripts/setup-rt.sh`
- 可选：RAWmakase（RAW 预览与过曝修正）

## 许可证

- 原创代码、脚本、文档、look 配置：**0BSD**（见 `LICENSE`）
- 内置 YuNet 模型：**MIT**（见 `skills/photo-auto-beautify/assets/models/LICENSE`）
- RawTherapee：**GPLv3**，仅按需下载，不随仓库分发
- OpenCV / NumPy / Pillow / Python：各自许可证

详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 隐私

人脸与照片处理全部在本地完成，不上传照片或人脸数据。

---

完整策略以英文 [`SKILL.md`](skills/photo-auto-beautify/SKILL.md) 为准；本页仅作中文补充。
