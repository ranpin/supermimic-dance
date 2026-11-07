# supermimic-dance

> 🎬 **在线 Demo**：<https://ranpin.github.io/supermimic-dance/>

2025 春晚舞蹈视频 → 物理仿真 Unitree G1 零样本跳舞：单目群舞视频经 PromptHMR + GMR 重定向为 9 名舞者的 G1 参考动作，由 SuperMimic 复现策略（98k checkpoint，LAFAN1 训练）在 MuJoCo 物理仿真中零样本跟踪——**9/9 全片（39.3s）完片零失败**（return 0.639–0.760，关节 MAE 6.5–8.2°，正落在该策略的 OOD 发布带），高潮选段（29–37s）9/9 完片。纯仿真 demo，无真机、无微调。

本仓是 [spring-festival-dance-robot](https://github.com/ranpin/spring-festival-dance-robot)（运动学重定向回放）的「物理版续作」：同一支视频、同一份重定向产物，从「回放关节角」升级为「物理机器人自己平衡着把舞跳出来」。

## 结果速览

| 评测 | 动作来源 | 完片 | return | 关节 MAE | 对齐 MPJPE |
|---|---|---|---|---|---|
| 全片 39.3s | 9 名舞者视频重定向动作 | 9/9 | 0.639–0.760 | 6.5–8.2° | 4.8–6.4cm |
| 高潮选段 8s（29–37s） | 同上（共同时间窗） | 9/9 | 0.553–0.764 | 5.8–8.4° | 4.6–7.3cm |
| 参照：LAFAN1 库内（发布值¹） | mocap 重定向 40 条 | 40/40 | 0.871 | 4.4° | — |
| 参照：100STYLE OOD（发布值¹） | 未见 mocap 3573 条 | 3569/3573 | 0.805 | 7.0° | — |

¹ 发布值来自 SuperMimic-MuJoCo README（同一 98k checkpoint）。指标口径与逐舞者明细见 demo 页「评测结果」节。

## 管线

```
舞蹈视频 ─PromptHMR→ SMPL-X ─GMR→ G1 关节序列 (30fps)
  ─格式转换→ SuperMimic 98k 策略零样本跟踪 (MuJoCo, 50Hz) ─→ 评测 / 渲染
```

## 仓库结构

- `convert_spring_dance.py` — GMR 产物 pkl → SuperMimic joblib 格式（xyzw 四元数 / SDK 关节序天然兼容，纯字段映射）
- `select_excerpt.py` — rollout 滑窗选段（跟踪误差 × 舞蹈强度）
- `make_label.py` / `composite_demo_videos.sh` — 中文标签条渲染与 ffmpeg 合成
- `motions/spring/` — 9 名舞者重定向动作 + `spring_excerpts.pkl` 共窗选段
- `eval/` — 评测产物（evaluation.json / tracking_metrics.json）
- `docs/` — demo 页（GitHub Pages）

## 复现

依赖 [SuperMimic-MuJoCo](https://github.com/panhainan2020/SuperMimic-MuJoCo)（自带 98k checkpoint；macOS arm64 纯 CPU 评测已实测可行）与 spring-festival-dance-robot 的 Kaggle 重定向产物。完整步骤见 [docs/REPRODUCE.md](docs/REPRODUCE.md)。

## 致谢与来源

- SuperMimic：Liao, Abbeel, Sreenath（UC Berkeley），arXiv 2610.28480
- SuperMimic-MuJoCo 移植与 98k checkpoint：[panhainan2020/SuperMimic-MuJoCo](https://github.com/panhainan2020/SuperMimic-MuJoCo)
- GMR：[YanjieZe/GMR](https://github.com/YanjieZe/GMR)（ICRA 2026，arXiv 2510.02252）；PromptHMR 与 video2robot 管线：Datawhale every-embodied 春晚舞蹈机器人教程（经 spring-festival-dance-robot vendored）
- 相关先行工作：[seerier/Humanoid-Motion](https://github.com/seerier/Humanoid-Motion)（视频 → GVHMR → GMR → SuperMimic/BeyondMimic 零样本跟踪）
- LAFAN1：Ubisoft La Forge（CC BY-NC-ND 4.0）；G1 重定向版取自 [lvhaidong/LAFAN1_Retargeting_Dataset](https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset)
- 输入视频：2025 春晚舞蹈片段（Datawhale 教程自带 dance_1.mp4）

## License

代码 MIT（LICENSE）；文档与页面 CC-BY-4.0。视频资产含 2025 春晚画面，版权归原版权方，仅作非商业技术演示。
