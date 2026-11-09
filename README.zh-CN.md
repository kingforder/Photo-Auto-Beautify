# Photo Auto Beautify · 本地免费批量图片美化

**这是一个导入智能体使用的 Agent Skill。**

[English](README.md) | **简体中文**

> 不订阅、不上传、不逐张修图：导入智能体后，由智能体理解你的偏好、选择参数并执行本地流水线。

> **这不是让用户手敲命令的 CLI 工具。** 命令行是底层实现方式，智能体会根据
> “自然一点 / 脸再白一点 / 连拍只留最好的 / 不要动原片”等个性化要求调整
> 档位、预设、连拍策略和清理行为；用户不需要背参数。

底层是纯命令行照片流水线：正常片自动美化，明显问题生成修正候选并询问，疑似问题只给建议。

## 能力

- 自动分诊：正常 / 明显问题 / 疑似问题，整图模糊单独提示；
- 来源感知：读取 EXIF `Make`/`Model`，手机默认均衡档（可降到低档），相机默认高档，来源不明时用均衡档兜底；
- 降噪与锐化：按来源/ISO 自动选择轻度或中度降噪，相机默认轻度输出锐化；这里的“锐度”是边缘 acutance，不是凭空增加细节；
- 低风险收尾：受限的中性色白平衡、带肤色/中性色保护的 Vibrance、轻高光 shoulder；不自动做风格转换；
- 场景感知：人像、夜景、高调、风景、通用；
- 四档强度：`min` 自然 / `medium` 均衡 / `high` 出片 / `max` 更重（允许调过头）；`--strength` 可强制所有照片使用同一档；
- 人像：使用更轻的基础 look + 全局肤色 LUT，不做人脸抠图、蒙版磨皮或局部美白；LUT 按颜色相似度平滑提亮肤色，脸/脖子/手一起自然过渡；手机均衡档的 LUT 比相机高档更轻；检测人脸饱和度，已经饱和时改用中性基础配置；读取时识别 ICC（DCI-P3→sRGB）；
- 风格：黑白、轻/强去雾、夜景、食物，配置可扩展；
- 选片：模糊、曝光异常、近似重复，只报告不删图；
- 连拍：检测分组，每组默认只留 1 张最佳帧（最多 2 张，且仅当第二张确有明显不同的表情/姿势/瞬间），可选像素堆叠或动态 WebP/GIF；最佳帧留在原文件夹，`--apply-cleanup` 可将剩余连拍 RAW 移入待删除文件夹（默认关闭、只移动不删除）；
- 多格式输入，统一输出 JPEG；
- 原图保护、统一命名、修正候选确认、清理中间产物。

## 基于开源组件

这不是黑盒工具：每一步处理都建立在开源组件上，skill 本身使用 **0BSD**。

| 组件 | 用途 | 许可证 |
| --- | --- | --- |
| **RawTherapee** | RAW/JPEG/PNG/TIFF 渲染 | GPLv3 |
| **YuNet**（OpenCV Zoo） | 人脸检测 | MIT |
| **OpenCV** | 人脸检测、图像分析 | Apache-2.0 |
| **NumPy** | 数值分析 | BSD-3-Clause |
| **Pillow** | 图像读写与格式转换 | HPND |
| **Python** | 运行时 | PSF |
| **pillow-heif**（可选） | HEIC/HEIF 解码 | BSD-3-Clause |
| **ffmpeg**（可选） | JPEG XL 解码 | 取决于构建 |
| **RAWmakase**（可选） | RAW 预览与曝光修正 | MIT |

不需要专有 SDK、云 API、账号或订阅；脚本全部可读、全部本地运行。
RawTherapee 从官方 release 下载，YuNet 模型随包保留 MIT 声明并校验 SHA256。
完整清单（含编解码器许可证）见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 支持的格式

RAW（RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW 等）、JPEG、PNG、TIFF、
WebP、AVIF、HEIC/HEIF、JPEG XL、BMP、GIF（首帧）；输出统一 JPEG。

HEIC 需要 `pillow-heif`；JXL 需要 `ffmpeg`（libjxl）。

## 默认规则

| 分类 | 处理 |
| --- | --- |
| 正常 | 按来源自动选档：手机 `medium`（可 `min`），相机 `high`，来源不明 `medium`；`--strength` 强制统一档位 |
| 明显问题 | 保留原图，生成 `<原名>-fixed.jpg` 候选，再询问 |
| 疑似问题 | 只给建议，不生成文件 |
| 明显但无法修复 | 整图模糊等只提示重拍/检查对焦 |

来源判定只看 EXIF `Make`/`Model`，不猜文件名：

| 来源 | 默认档位 | 人像处理 |
| --- | --- | --- |
| 手机 | `medium`（要更自然用 `--phone-strength min`） | 轻基础 look + 0.65 LUT（`min` 为 0.35） |
| 相机 | `high` | 轻基础 look + 1.0 LUT |
| 不明 | `medium` | 保守兜底，避免把去 EXIF 的手机片修重 |

- RAW 的 `Make`/`Model` 需要 `exiftool` 兜底；没有时按“来源不明”走 `medium`。
- `--source phone|camera|unknown` 可在 EXIF 缺失或识别错误时强制来源。

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
  --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

- `--strength auto`：默认；读取 EXIF `Make`/`Model`，手机 → `medium`，相机 → `high`，来源不明 → `medium`。
- `--phone-strength min|medium`：把手机档降得更低（默认 `medium`）。
- `--source auto|phone|camera|unknown`：EXIF 缺失或识别错误时强制来源。
- `--denoise auto|off|light|medium|strong`：降噪；`auto` 只对手机/高 ISO 保守处理。
- `--sharpen auto|off|light|medium|strong`：输出锐化；`auto` 只给相机轻度锐化。
- `--wb auto|off`：只修正高置信度的中性色偏，最多 2 个 LAB 单位。
- `--vibrance auto|off|light|medium`：提升低饱和色彩，保护肤色和中性色。
- `--highlight-rolloff auto|off|light|medium`：轻压高光肩部，不恢复已死白细节。
- `--strength min|medium|high|max`：强制所有照片使用同一档；`max` 会明显更重，给“就要好看”的用户。
- `--dry-run`：只输出分诊计划；
- `--temp-dir`：受限环境指定可写临时目录；
- 跑完先看报告，再确认 `*-fixed.jpg` 是否保留。

Linux / WSL：

```bash
cd skills/photo-auto-beautify
# 仅 Debian/Ubuntu，缺 venv/pip 时：
# sudo apt install python3-venv python3-pip
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-rt.sh
python3 scripts/photo-pipeline.py \
  --input "$HOME/photos" --output-dir "$HOME/photos" \
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
- 可选：`exiftool`（RAW 来源识别；没有时 RAW 按“来源不明”走 `medium`）
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
