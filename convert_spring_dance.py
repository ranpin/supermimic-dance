#!/usr/bin/env python3
"""Convert video2robot/GMR robot_motion*.pkl to SuperMimic-MuJoCo joblib motion format.

Conventions verified 2026-11-03 (no data transformation needed beyond renaming):
- root_rot: GMR saves xyzw (GMR data_loader.py converts xyzw->wxyz on load);
  SuperMimic motion.py expects xyzw. Empirically confirmed (yaw-dominant z column).
- dof_pos: GMR returns mujoco qpos of g1_mocap_29dof.xml, whose joint order is
  identical to SuperMimic g1_29dof.xml (Unitree SDK order).
- root_pos: meters, z-up, world frame; the SuperMimic loader applies no floor
  or heading fix, so values are passed through as-is.

Usage: convert_spring_dance.py DST.pkl NAME=SRC.pkl [NAME=SRC.pkl ...]
"""
import pickle
import sys

import numpy as np


def convert(src):
    with open(src, "rb") as f:
        d = pickle.load(f)
    if d.get("robot_type") != "unitree_g1":
        raise ValueError(f"{src}: robot_type={d.get('robot_type')!r}, expected unitree_g1")
    rp = np.asarray(d["root_pos"], dtype=np.float64)
    rr = np.asarray(d["root_rot"], dtype=np.float64)
    dp = np.asarray(d["dof_pos"], dtype=np.float64)
    fps = float(d["fps"])
    T = int(d["num_frames"])
    if rp.shape != (T, 3) or rr.shape != (T, 4) or dp.shape != (T, 29):
        raise ValueError(f"{src}: shapes {rp.shape} {rr.shape} {dp.shape} vs T={T}")
    if not (np.isfinite(rp).all() and np.isfinite(rr).all() and np.isfinite(dp).all()):
        raise ValueError(f"{src}: non-finite values")
    dev = float(np.abs(np.linalg.norm(rr, axis=1) - 1).max())
    if dev > 1e-3:
        raise ValueError(f"{src}: quaternion norm deviation {dev}")
    return {"root_trans_offset": rp, "root_rot": rr, "dof_pos": dp, "fps": fps}


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    dst, pairs = sys.argv[1], sys.argv[2:]
    out = {}
    for pair in pairs:
        name, src = pair.split("=", 1)
        clip = convert(src)
        out[name] = clip
        T = clip["root_trans_offset"].shape[0]
        print(f"  {name}: T={T} ({T / clip['fps']:.1f}s) fps={clip['fps']:g} "
              f"root_z0={clip['root_trans_offset'][0, 2]:.3f} <- {src}")
    try:
        import joblib
        joblib.dump(out, dst)
    except ImportError:
        # SuperMimic's loader uses joblib.load, which also reads plain pickles.
        with open(dst, "wb") as f:
            pickle.dump(out, f, protocol=4)
        print("  (joblib unavailable in this env; wrote plain pickle)")
    print(f"wrote {dst}: {len(out)} clip(s) {sorted(out)}")


if __name__ == "__main__":
    main()
