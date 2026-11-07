# 风格预设与实测边界

测试图：Wikimedia Commons 的 CC BY-SA 4.0 样图（雾景、建筑、食物），以及用户测试集里的夜景/人像。
仅本地测试，不随 skill 分发原图。

## 黑白

`assets\looks\rt-bw.pp3`（自写 Desaturation 配置，不复制 RawTherapee 的 GPL 配置）

```powershell
powershell -File scripts\rt-batch.ps1 -InputDir $dir -Suffix "-bw" `
  -ProfileOnly -LookProfile assets\looks\rt-bw.pp3
```

- 建筑、纪实、硬光人像效果好；
- 高光片可能偏亮，批量前看一张；
- 不要和 Auto-Matched 叠（会二次改曲线），所以用 `-ProfileOnly`。

## 去雾

- `assets\looks\rt-dehaze.pp3`：Strength 55 / Depth 45 / Saturation 25，轻微；
- `assets\looks\rt-dehaze-strong.pp3`：Strength 85 / Depth 60 / Saturation 30，更强。

```powershell
powershell -File scripts\rt-batch.ps1 -InputDir $dir -Suffix "-dehaze" `
  -ProfileOnly -LookProfile assets\looks\rt-dehaze.pp3
```

实测：JPG 雾景上效果偏温和，主要提升前景对比；RAW 的余量更大。强档会把天空压暗，先试样。
去雾不是“换天”，不能恢复被雾完全遮住的远景细节。

## 夜景 / 低光

用较高 ISO 的降噪配置，再叠 look2：

```powershell
powershell -File scripts\rt-batch.ps1 -InputDir $dir -Suffix "-night" `
  -IsoProfile High -LookProfile assets\looks\rt-look2.pp3
```

- 实测夜景 JPG：灯光高光保持，暗部噪点降低；
- 强降噪会抹掉细节，人像/纹理多的场景用 Medium；
- 不要用去雾或强对比处理夜景，容易把天空压死。

## 食物 / 高调静物

- 推荐：`-LookProfile assets\looks\rt-look2.pp3`（对比/饱和适中）；
- **不要用 Pop 1**：实测白色盘子直接过曝，高光丢失；
- 食物通常需要更暖的白平衡，可在 RT 里单独调 Temperature/Tint，不建议全局预设硬套。

## 建筑 / 透视

- 目前没有可靠的纯 CLI 自动透视校正；RawTherapee GUI 有 Perspective → Automatic，需要目视确认；
- 可以用 `-ProfileOnly -LookProfile rt-look2.pp3` 做基础影调，透视留给人手；
- 镜头畸变/暗角可由 Auto-Matched 配置里的 LensProfile 处理。

## 结论

| 需求 | 可自动化 | 建议 |
| --- | --- | --- |
| 黑白 | 是 | `rt-bw.pp3`，ProfileOnly |
| 去雾 | 部分 | 轻档先试，强档谨慎 |
| 夜景降噪 | 是 | ISO High/Medium + look2 |
| 食物 | 部分 | look2；不要 Pop 1 |
| 建筑透视 | 否（需目视） | GUI/手动 |
| 换天/生成式 | 否 | 不在本 skill 范围 |
