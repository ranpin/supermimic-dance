# 复现步骤

全链在 macOS arm64 纯 CPU 实测可行（SuperMimic-MuJoCo 官方仅在 Linux x86_64 + Python 3.10 验证过，Mac 注意事项见 §1）。评测为确定性仿真，无 seed 方差。

## 0. 前置

- macOS arm64（或 Linux x86_64）；Python 3.10–3.12；[uv](https://docs.astral.sh/uv/)（或 venv+pip）
- 春晚重定向产物：[spring-festival-dance-robot](https://github.com/ranpin/spring-festival-dance-robot) 的 Kaggle 管线输出 `robot_motion_track_{1..9}.pkl`（fps=30、root_pos/root_rot(xyzw)/dof_pos(29, SDK 序)），或自行重跑该仓 Kaggle kernel

## 1. 安装 SuperMimic-MuJoCo

```bash
git clone https://github.com/panhainan2020/SuperMimic-MuJoCo
cd SuperMimic-MuJoCo
uv venv .venv --python 3.12
# macOS：不要用官方 requirements.lock.txt（含 Linux CUDA 运行时包），按 pyproject 纯依赖装；
# 境内网络 PyPI 直连慢（实测 ~400KB/s）时换清华源：
uv pip install --python .venv/bin/python \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple -e '.[video]'
.venv/bin/python -c "import torch, mujoco, mjlab, supermimic; print('OK')"
OMP_NUM_THREADS=2 .venv/bin/python -m unittest discover -s tests   # 43 项契约检查
```

98k checkpoint（`checkpoints/g1_29dof/policy_098000.pt`，36.5MB）随仓附带，无需另下。

## 2. 转换重定向产物 → SuperMimic 格式

```bash
python convert_spring_dance.py motions/spring/spring_dance_track1.pkl \
  "spring_dance_track1=<path>/robot_motion_track_1.pkl"
```

GMR 产物与 SuperMimic joblib 格式天然兼容（root_rot 已是 xyzw、dof_pos 已是 Unitree SDK 关节序、米制 z-up），转换为纯字段映射，脚本内含形状/有限性/四元数范数断言。

## 3. 全片评测（CPU）

```bash
export SUPERMIMIC_EXPERIMENT_ROOT=<本仓>/eval
cd <SuperMimic-MuJoCo>
OMP_NUM_THREADS=4 .venv/bin/python -m supermimic.evaluate \
  --backend mujoco --device cpu --robot g1_29dof \
  --profile upstream --observation_mode legacy99 --network_size paper \
  --motion_dir <本仓>/motions/spring/spring_dance_track1.pkl \
  --ckpt checkpoints/g1_29dof/policy_098000.pt \
  --run_dir "$SUPERMIMIC_EXPERIMENT_ROOT/crux_spring_track1" \
  --record "$SUPERMIMIC_EXPERIMENT_ROOT/crux_spring_track1/rollout.npz"
```

结果以 `evaluation.json` 为准（归一化 return + 完片/失败标签）；姿态诊断：

```bash
.venv/bin/python tools/analyze_rollout.py --record .../rollout.npz \
  --evaluation .../evaluation.json --output .../tracking_metrics.json --robot g1_29dof
```

## 4. 选段 + 选段评测

```bash
python select_excerpt.py eval/excerpts_all9.json \
  track1=eval/crux_spring_track1/rollout.npz ... track9=eval/crux_spring_track9/rollout.npz
```

规则：8s 滑窗（50Hz rollout 空间），存活门 + 跟踪误差 ≤ 中位数的窗口里挑参考关节角速度（舞蹈强度）最大者。demo 用的**共窗** [29,37]s 在此基础上加「平均强度 ≥80°/s」门后取最差舞者误差最小（保证 9 机时间对齐）。裁剪 9 条动作到共窗合成 `motions/spring_excerpts.pkl`（单 joblib 多 clip），重跑 §3 一次评完 9 条。

## 5. 渲染 + 合成

```bash
# 渲染（macOS 用 --gl glfw；EGL 为 NVIDIA 默认）
.venv/bin/python tools/render_rollout.py \
  --record "$SUPERMIMIC_EXPERIMENT_ROOT/excerpts_common/rollout.npz" \
  --clip excerpt_track4 --output "$SUPERMIMIC_EXPERIMENT_ROOT/assets/hero_track4_ghost.mp4" \
  --robot g1_29dof --comparison ghost --gl glfw
# 网格面板：--comparison policy --width 320 --height 240，逐 clip 渲染 9 条

# 标签条 + 合成（本仓）
python make_label.py eval/assets/label_hero.png 1494 120 "<行1>" "<行2>" "<行3>"
bash composite_demo_videos.sh
```

## Sanity 评测（可选，验证 harness + checkpoint）

LAFAN1 G1 重定向 CSV：从 [lvhaidong/LAFAN1_Retargeting_Dataset](https://huggingface.co/datasets/lvhaidong/LAFAN1_Retargeting_Dataset) 下载 `g1/*.csv`（境内被墙走 `hf-mirror.com` 同路径），`--motion_dir` 指向该目录。发布口径：40/40 完片、return 0.8713、关节 MAE 4.40°；本仓 macOS 实测 2 条（dance1+walk1）return 0.887、0 失败。
