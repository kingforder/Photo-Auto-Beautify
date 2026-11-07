# Photo Auto Beautify · 本地免费批量图片美化

> 不订阅、不上传、不逐张修图：一条命令把整批 RAW/JPG/HEIC 出成可交付成片。

纯命令行照片流水线 skill：正常片自动美化，明显问题生成修正候选并询问，疑似问题只给建议。

- 默认中档美化；`--strength min/medium/max` 可选最低/最高档。
- RAW 正常片输出与 RAW 同名的 JPG；其他格式输出 `<原名>-beauty.jpg`。
- 明显过曝/欠曝：保留原图，生成 `<原名>-fixed.jpg`，由用户确认是否保留。
- 疑似问题/整图模糊：只给建议，不生成文件。
- 最终只保留原图 + 美化文件 + 修正候选；预览/暂存会清理。

## 支持格式

RAW（RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW 等）、JPEG、PNG、TIFF、
WebP、AVIF、HEIC/HEIF、JPEG XL、BMP；输出统一 JPEG。
HEIC 需要 `pillow-heif`，JXL 需要 `ffmpeg`（libjxl）。

## 依赖

- Python 3 + Pillow + NumPy + OpenCV（人脸/选片/格式转换）
- `pillow-heif`（HEIC/HEIF），`ffmpeg`（JPEG XL）
- RawTherapee 5.13 便携版（GPLv3，`scripts/setup-rt.ps1` 下载）
- 可选：RAWmakase（RAW 预览与过曝修正）

## 安装与使用

仓库发布到 GitHub 后：

```bash
npx skills add <owner>/photo-auto-beautify
```

或手动复制 `skills/photo-auto-beautify/` 到 agent 的 skills 目录。

Windows 示例：

```powershell
$env:PYTHONPATH = "..\face-deps"
python scripts\photo-pipeline.py --input "C:\photos" --output-dir "C:\photos" `
  --strength medium --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

## 许可证

- 本项目原创代码、脚本、文档、look 配置：**0BSD**（见 `LICENSE`）。
- 内置 YuNet 模型：**MIT**（见 `assets/models/LICENSE`）。
- RawTherapee：**GPLv3**，仅按需下载，不随本仓库分发。
- OpenCV / NumPy / Pillow / Python：各自许可证，运行时安装。

详见 `THIRD_PARTY_NOTICES.md`。

## 隐私

人脸处理与照片分析全部本地完成，不上传照片或人脸数据。
