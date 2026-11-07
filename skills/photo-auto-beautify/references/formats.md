# 输入格式矩阵

默认输出统一为 JPEG；RAW 正常片输出与 RAW 同名的 `.jpg`，其他格式输出
`<原名>-beauty.jpg`。

| 输入 | 解码方式 | 状态 |
| --- | --- | --- |
| RAW：RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW/…（完整列表见 `scripts/image_formats.py`） | RawTherapee | 原生 |
| JPEG / PNG / TIFF | RawTherapee | 原生 |
| WebP | Pillow → 工作 TIFF → RawTherapee | 支持 |
| AVIF | Pillow（Pillow 12+ 内置 AVIF）→ TIFF | 支持 |
| HEIC / HEIF | pillow-heif → TIFF | 支持（需安装 pillow-heif） |
| JPEG XL (.jxl) | ffmpeg（libjxl）→ TIFF | 支持（需 ffmpeg） |
| BMP | Pillow → TIFF | 支持 |
| GIF（静态首帧） | Pillow → 工作 TIFF | 支持（首帧） |

## 依赖

- `opencv-python-headless`、`numpy`、`Pillow`：人像/选片/格式转换；
- `pillow-heif`：HEIC/HEIF。`setup-face.ps1` 会尝试安装；
- `ffmpeg`（带 libjxl）：JPEG XL。可用 `FFMPEG` 环境变量指定路径；
- RawTherapee：RAW/JPEG/PNG/TIFF 的渲染。

缺少 HEIC/JXL 解码器时，流水线会在报告的“读取/转换失败”里列出原因，不会中断整批。

## 局限

- 输出统一 JPEG；暂不输出 AVIF/HEIC/JXL（RawTherapee 不支持这些输出）。
- 动图/多图容器只取主图/首帧。
- 16-bit TIFF/PNG 输入会按 8-bit 工作副本处理（最终 JPEG 8-bit）。
- RAW 的相机型号支持范围由 RawTherapee 5.13 决定；极新机型可能未支持。

## 实测

- PNG/TIFF：RawTherapee 直接处理；
- WebP/AVIF/HEIC：转工作 TIFF 后 RT 输出成功；
- JXL：ffmpeg 解码为 16-bit TIFF 后 RT 输出成功；
- 输出命名已按原文件 basename，不再出现 `sample-normalized-beauty` 这类中间名。
