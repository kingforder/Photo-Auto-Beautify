---
name: photo-auto-beautify
description: 批量美化 RAW/JPG 照片：正常片按中档自动美化，明显问题自动生成修正候选并询问，疑似问题只给建议；纯命令行，保留原图，不保留中间结果。
license: 0BSD
---

# Photo Auto Beautify

纯命令行照片流水线：先判断“正常 / 明显问题 / 疑似问题”，再分别处理。正常片自动美化；明显问题生成修正候选后由用户确认；疑似问题只提示不产出文件。

## 适用

- 用户要求“批量一键美化”“把这批照片调一下”“看看哪些照片曝光不正常”。
- 输入是 RAW（RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW）或 JPG/TIFF。
- 要求 shell 自动化、可复现、不依赖 GUI。

## 不适用

- 需要换天、生成式修改、瘦脸/改五官。
- 期待“AI 理解画面意图”：本流程是规则化影调/色彩 + 人脸检测，不认识所有场景语义。

## 核心原则

1. **原片永不修改**；只新增结果文件。
2. **正常片**：默认中档美化；用户声明 `min`/`max` 时才用最低/最高档。
3. **明显问题**：保留原图，自动生成 `*-fixed.jpg` 修正候选，然后询问用户是否保留。
4. **疑似问题**：只给建议，不生成任何修复文件。
5. 最终只保留：原图 + 美化文件 + 修正候选；预览/暂存等中间结果全部清理。
6. 不能把“过曝/死黑/严重模糊”说成可自动恢复；算法不能无中生有。

## 依赖

- RawTherapee 5.13 便携版（GPLv3）：
  `..\rt-5.13\RawTherapee_5.13_win64_x86_64_release\`
  含 `rawtherapee-cli.exe` 与 `profiles\Auto-Matched Curve - ISO Low/Medium/High.pp3`。
  首次使用可运行 `scripts\setup-rt.ps1` 下载并校验（约 121 MB）；也可手动放置后用
  `-RtRoot` 指向 `RawTherapee_5.13_win64_x86_64_release` 文件夹。
- 异常体检可选依赖 RAWmakase（用于把 RAW 渲染成小预览）：
  `%LOCALAPPDATA%\Programs\RAWmakase\rawmakase.exe`。
- Python 3 + Pillow + numpy + OpenCV（体检/人像/选片脚本）。

## 默认流水线（推荐）

```powershell
$env:PYTHONPATH = "..\face-deps"
python scripts\photo-pipeline.py `
  --input "C:\photos" --output-dir "C:\photos" `
  --strength medium `
  --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

- `--strength medium`（默认）：正常片中档美化；用户声明最低/最高时改 `min`/`max`。
- `--dry-run`：只输出分类/计划，不生成结果。
- 在受限 agent 环境里，`--temp-dir` 指到工作区可写目录；普通用户可省略。

输出规则：

| 输入 | 分类 | 输出 |
| --- | --- | --- |
| RAW 正常 | ok | **`<原名>.jpg`**（与 RAW 同名；已存在则 `<原名>-beauty.jpg`） |
| JPG 正常 | ok | `<原名>-beauty.jpg` |
| RAW/JPG 明显问题 | obvious | `<原名>-fixed.jpg`（候选，等用户确认） |
| 疑似/无法修复 | suspect/blur | 不生成文件，只写建议 |

场景自动检测与预设：

| 场景 | 判定 | 预设 |
| --- | --- | --- |
| portrait | 检测到 1–3 张可用人脸 | look1/2/3 + 人脸皮肤平滑（同档位） |
| night | 平均亮度 ≤75 且非高光为主 | ISO High + look1/2/3 |
| highkey | 平均亮度 ≥175、暗部极少 | look1/2/3（不套 Pop 1） |
| landscape | 动态范围较窄/常规风景 | look1/2/3 |
| general | 其余 | look1/2/3 |

分类规则（脚本内置）：

- **明显问题**：全局过曝/洗白、全局欠曝；会自动生成 `-fixed` 候选。
- **明显但无法修复**：整图模糊；只建议重拍/检查对焦，不生成文件。
- **疑似问题**：局部高光、偏暗夜景/剪影、低对比、清晰度偏低；只给建议。
- 人像的亮天空不会被误判为“高光偏多”；合影 >3 张可用人脸时跳过人脸美化。

跑完后必须向用户确认：`*-fixed.jpg` 是否保留；确认前不要删除原图。
中间预览/暂存由脚本清理，最终只留原图 + 美化文件 + 修正候选。

## 手动分步（可选，用于解释/调试）

### 1. 盘点

```powershell
Get-ChildItem $InputDir -File | Group-Object Extension | Select-Object Name,Count
```

确认 RAW 数、原始 JPG 数、已有 `-rt*` 输出数；输出不得覆盖原片。

### 2. 异常体检（手动排查，用于解释分类）

正式批量请用上面的 `photo-pipeline.py`；这一步只用于抽检和解释为什么某张被标为疑似。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\render-previews.ps1 `
  -InputDir $InputDir -PreviewDir ..\check-tmp -MaxEdge 900

python scripts\check-images.py `
  --images $InputDir --previews ..\check-tmp `
  --report ..\image-check-report.md
```

判读规则（脚本内置，只用于提示）：

- `mean≥200 且 range≤80 且 hot≥20` → 强提示全局过曝/洗白；
- `mean≤25 且 dark≥40` → 强提示全局欠曝；
- `hot≥8` → 高光裁切明显；`hot≥3` → 局部高光；
- `mean≤55 且 dark≥8` → 偏暗（可能是夜景/剪影）；
- 其余正常。

对每个提示给出**建议**，例如：过曝可试 `-2.5 EV + 高光 -100 + 阴影 +20 + 去雾 15`；亮天空/夜景/剪影倾向正常；不要自动应用。

### 2.5 选片 / 质量筛查（可选，只报告）

```powershell
python scripts\photo-cull.py --input $InputDir --report ..\cull-report.md
```

- 整图清晰度（拉普拉斯方差）标“相对模糊”；
- 亮度/高光/暗部提示；
- 近似重复按 aHash 分组，并用清晰度差 >3 排除“模糊版 vs 清晰版”误判；
- **只报告，不删图**。模糊/重复是否保留由用户判断。

### 3. 选择强度

| 档位 | 配置 | 用途 |
| --- | --- | --- |
| 下限 `-rt` | 仅 `Auto-Matched Curve - ISO Low.pp3` | 相机匹配/参考；JPG 基本 no-op |
| 默认 `-rt2` | + `assets\looks\rt-look2.pp3` | 自然去灰，推荐 |
| 上限 `-rt3` | + `assets\looks\rt-look3.pp3` | 低饱和场景更浓；饱和主体慎用 |
| 诊断 `look4` | + `assets\looks\rt-look4.pp3` | 只用于找崩点，不交付 |

### 3.5 风格预设（按题材）

| 需求 | 用法 |
| --- | --- |
| 黑白 | `-ProfileOnly -LookProfile assets\looks\rt-bw.pp3` |
| 去雾（轻） | `-ProfileOnly -LookProfile assets\looks\rt-dehaze.pp3` |
| 去雾（强） | `-ProfileOnly -LookProfile assets\looks\rt-dehaze-strong.pp3` |
| 夜景降噪 | `-IsoProfile High -LookProfile assets\looks\rt-look2.pp3` |
| 食物/高调 | `-LookProfile assets\looks\rt-look2.pp3`；**不要用 Pop 1**，白盘会过曝 |
| 建筑透视 | 纯 CLI 不可靠，需 GUI/手动；先做影调即可 |

`-ProfileOnly` 会跳过 Auto-Matched，只套指定 look；黑白/去雾必须这样用，避免二次改曲线。
实测与边界见 [references/styles.md](references/styles.md)。

### 4. 批量渲染

```powershell
powershell -ExecutionPolicy Bypass -File scripts\rt-batch.ps1 `
  -InputDir $InputDir -OutputDir $WorkDir -Suffix "-rt2" `
  -IsoProfile Low -LookProfile assets\looks\rt-look2.pp3
```

- 脚本先把 RT 输出写到 `%TEMP%\rtb`，再复制到 `OutputDir`，避免 RT 写中文/长路径失败。
- 如果当前 shell 被提权/受限，RT 子进程可能不能写 TEMP：**分两步**——
  1. 普通权限渲染到工作区；
  2. 单独提权 `Copy-Item` 到目标目录。

### 5. 校验

- 输出数 = 输入数（RAW + JPG）；
- 抽查 3 张尺寸/大小；
- 若目标目录有旧 `-rt*`，用新后缀（如 `-rt2`）避免覆盖；
- 统计 `-rt`→`-rt2` 的饱和度/对比增益，确认不是 no-op。

### 6. 报告

模板：

```text
完成：N 张（RAW x + JPG y），失败 z。
输出：<dir>\*-rt2.jpg
异常：P1021922 全局过曝（mean 242.7 / hot 43.9%），建议手动 -2.5EV；未自动修改。
正常：…
```

## 强度与上下限

详见 [references/limits.md](references/limits.md)。核心结论：

- 下限是“相机匹配”，JPG 几乎不变；
- `-rt2` 是通用默认；全量平均饱和 +5.8；
- `-rt3` 再 +3.2，收益递减；低饱和场景可用，饱和主体会先丢通道细节；
- 绝对上限：过曝/死黑/严重欠曝无法自动恢复；
- 停止条件：任何通道开始裁切（`clipany` 上升）就不要再加对比/饱和。

## 人像 / 人脸（可选）

仅当用户明确要求“人像优化/人脸美化”时启用；**不要默认对所有照片跑**。

- 先 `--dry-run` 报告检测到几张脸，不写图；
- 选 2–3 张代表图出强度 1/2/3 样片；
- 默认强度 2；强档 3 容易磨皮过度；
- 只做皮肤平滑 + 轻微眼白/牙齿提亮；**不瘦脸、不改变五官、不生成内容**；
- 默认跳过小于画面宽度 4% 的背景脸/误报（`--min-face-ratio`）；
- 输出 `-face.jpg`，原图不动；无脸图片跳过并报告。

```powershell
$env:PYTHON = "C:\path\to\python.exe"
powershell -ExecutionPolicy Bypass -File scripts\setup-face.ps1

$env:PYTHONPATH = "..\face-deps"
python scripts\face-beautify.py --input $InputDir --dry-run --report .\face-dry.md
python scripts\face-beautify.py --input $InputDir --output $OutDir --strength 2 --report .\face-report.md
```

依赖：OpenCV headless + YuNet 模型（232 KB）。细节与限制见
[references/portrait.md](references/portrait.md)。

## Windows 坑

- PowerShell 5.1 里 RT 质量参数必须写成 `"-j92"`，不能写 `-j$Quality`（可能被拆参数，输出严重劣化）。
- RT 不能可靠写中文/长路径；必须走 `%TEMP%\rtb` 暂存再复制。
- 负数参数：`render` 用 `--exposure=-2.5`；RAWmakase `control set` 用 `-- -20`。
- 提权执行 RT 可能无法写 TEMP；用“普通权限渲染 + 提权复制”。

## RapidRAW 说明

RapidRAW v1.6.7 的 `export` CLI 只有 `--output/--format/--quality/--tiff-bit-depth/--keep-metadata/--adjustments`；Auto Adjust 是 GUI 的 Tauri 命令，**无 `--auto`**。纯 shell 自动美化不要选它；可 GUI Auto 一次后 CLI 导出。

## 文件

- `scripts\photo-pipeline.py`：三分类 + 自动美化/修正候选 + 报告。
- `scripts\rt-batch.ps1`：批量渲染（支持叠加 look）。
- `scripts\render-previews.ps1`：RAW → 小预览（检测用）。
- `scripts\check-images.py`：指标与异常报告。
- `scripts\photo-cull.py`：模糊/曝光/近似重复的选片报告。
- `scripts\setup-rt.ps1`：下载/校验 RawTherapee 便携版。
- `scripts\face-beautify.py`：人像皮肤平滑 + 眼白/牙齿轻微提亮。
- `scripts\setup-face.ps1`：安装 OpenCV、下载 YuNet 模型。
- `assets\models\face_detection_yunet_2023mar.onnx`：人脸检测模型。
- `assets\xmp\fix-over.xmp`：明显过曝的 RAW 修正候选。
- `references\portrait.md`：人像模块的限制与建议。
- `references\styles.md`：黑白/去雾/夜景/食物的实测边界。
- `assets\looks\`：look1/2/3/4、黑白、去雾、修正配置。
- `references\limits.md`：实测上下限与决策矩阵。

## 许可证

- 本项目原创代码、脚本、文档、look 配置：**0BSD**（见 `LICENSE`），无需署名。
- 内置 YuNet 模型：**MIT**（见 `assets/models/LICENSE`），保留版权与许可声明。
- RawTherapee：**GPLv3**，由 `setup-rt.ps1` 从官方 release 下载，不随本仓库分发。
- OpenCV / NumPy / Pillow / Python：各自许可证，运行时安装。
- 完整清单见 `THIRD_PARTY_NOTICES.md`。
