#!/usr/bin/env python3
"""Render the 9 independently simulated dance rollouts as one formation scene.

The 9 dancers never contact each other, so compositing the 9 recorded physics
rollouts into a single scene is physically equivalent to simulating them
together (kinematic replay of recorded states, not a re-simulation).

Camera: follow-cam locked on the smoothed 9-robot centroid (absorbs the common
global drift so the formation stays centered), distance derived from the max
robot distance to the centroid, azimuth follows the smoothed mean dancer yaw
only if the formation actually rotates (>15 deg span over the window).

Input:  excerpts_common/rollout.npz  (T, 9, *) time-aligned, 50 Hz
Output: formation mp4 (960x540 @50fps)

root_quat in the rollout is wxyz (verified against ref_root_R, err 3.5e-8).

Usage: render_formation.py ROLLOUT.npz OUT.mp4 [--max-frames N]
"""
import os

os.environ.setdefault("MUJOCO_GL", "glfw")

import argparse

import imageio.v2 as imageio
import mujoco
import numpy as np

ROBOT_XML = "/Users/ranpin/projects/SuperMimic-MuJoCo/supermimic/assets/robots/g1_29dof.xml"
N = 9
W, H = 960, 540
FOVY = 45.0  # model default; horizontal half-angle tan = tan(fovy/2) * aspect


def yaw_from_wxyz(q):
    w, x, y, z = q
    return np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def build_model():
    spec = mujoco.MjSpec()
    # offscreen framebuffer must cover the render size (model default is 640x480)
    spec.visual.global_.offwidth = W
    spec.visual.global_.offheight = H
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[50, 50, 0.05],
                            rgba=[0.30, 0.32, 0.36, 1.0])
    for pos, direction, diffuse in (
        ([3.5, -0.2, 8], [0, 0, -1], [0.75, 0.75, 0.75]),
        ([-3, -5, 6], [0.4, 0.6, -0.7], [0.35, 0.35, 0.38]),
    ):
        light = spec.worldbody.add_light()
        light.pos = pos
        light.dir = direction
        light.type = mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
        light.diffuse = diffuse
    for i in range(N):
        frame = spec.worldbody.add_frame(name=f"spawn{i}")
        spec.attach(mujoco.MjSpec.from_file(ROBOT_XML), prefix=f"g{i}_", frame=frame)
    return spec.compile()


def robot_geom_ids(model, i):
    # match by BODY name (geoms are often unnamed in MJCF; bodies/links are named)
    ids = set()
    for gid in range(model.ngeom):
        bid = model.geom_bodyid[gid]
        bname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid) or ""
        if bname.startswith(f"g{i}_"):
            ids.add(gid)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rollout")
    ap.add_argument("out")
    ap.add_argument("--max-frames", type=int, default=None)
    args = ap.parse_args()

    d = np.load(args.rollout, allow_pickle=True)
    root_p = d["root_p"].astype(np.float64)
    root_q = d["root_quat"].astype(np.float64)  # wxyz
    dof = d["q"].astype(np.float64)
    T = root_p.shape[0]
    if args.max_frames:
        T = min(T, args.max_frames)

    model = build_model()
    data = mujoco.MjData(model)
    assert model.nq == N * 36, f"nq={model.nq}, expected {N * 36}"
    base_adr, dof_adr = [], []
    for i in range(N):
        # qposadr comes back as a shape-(1,) numpy array — extract the scalar
        base_adr.append(model.joint(f"g{i}_floating_base_joint").qposadr.item())
        dadr = model.joint(f"g{i}_left_hip_pitch_joint").qposadr.item()
        assert model.joint(f"g{i}_right_wrist_yaw_joint").qposadr.item() - dadr == 28, \
            f"robot {i}: dof qpos not contiguous"
        dof_adr.append(dadr)

    # ---- follow camera from data ----
    cents = root_p[:T, :, :].mean(axis=1)  # (T,3)
    yaws_t = np.stack([np.array([yaw_from_wxyz(root_q[t, i]) for i in range(N)])
                       for t in range(T)])
    mean_yaw_t = np.arctan2(np.sin(yaws_t).mean(1), np.cos(yaws_t).mean(1))
    k = min(10, (T - 1) // 2)
    ker = np.ones(2 * k + 1) / (2 * k + 1)

    def smooth(a):
        return np.convolve(np.pad(a, (k, k), mode="edge"), ker, mode="valid")

    cent_s = np.stack([smooth(cents[:, 0]), smooth(cents[:, 1])], 1)
    yaw_s = smooth(np.unwrap(mean_yaw_t))
    yaw_span = float(np.degrees(yaw_s.max() - yaw_s.min()))
    follow_yaw = yaw_span > 15.0
    fixed_az = float(np.degrees(yaw_s.mean()) + 180.0)

    rel = np.linalg.norm(root_p[:T, :, :2] - cent_s[:, None, :], axis=-1)
    r_max = float(rel.max())
    th = np.tan(np.radians(FOVY / 2)) * (W / H)
    dist = float(np.clip((r_max + 0.9) / th, 4.0, 8.0))
    print(f"follow-cam: yaw span={yaw_span:.1f}deg (follow_yaw={follow_yaw}) "
          f"r_max={r_max:.2f}m -> distance={dist:.2f}")

    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.elevation = -12.0
    cam.distance = dist

    renderer = mujoco.Renderer(model, height=H, width=W)

    def set_pose(t):
        for i in range(N):
            data.qpos[base_adr[i]:base_adr[i] + 3] = root_p[t, i]
            data.qpos[base_adr[i] + 3:base_adr[i] + 7] = root_q[t, i]
            data.qpos[dof_adr[i]:dof_adr[i] + 29] = dof[t, i]
        mujoco.mj_kinematics(model, data)

    def set_cam(t):
        cam.lookat[:] = [cent_s[t, 0], cent_s[t, 1], 0.95]
        cam.azimuth = float(np.degrees(yaw_s[t]) + 180.0) if follow_yaw else fixed_az

    # framing check on sampled frames: all 9 robots visible via segmentation
    geom_ids = [robot_geom_ids(model, i) for i in range(N)]
    sample_ts = sorted({0, T // 4, T // 2, 3 * T // 4, T - 1})
    for attempt in range(3):
        all_ok, report = True, []
        for tf in sample_ts:
            set_pose(tf)
            set_cam(tf)
            renderer.update_scene(data, camera=cam)
            renderer.enable_segmentation_rendering()
            seg = renderer.render()
            renderer.disable_segmentation_rendering()
            vals = None
            for ch in (0, 1):  # encoding: one channel holds id+1; probe both
                cand = seg[:, :, ch]
                if all(set(np.unique(cand).tolist()) & {g + 1 for g in gids}
                       for gids in geom_ids):
                    vals = cand
                    break
            if vals is None:
                all_ok = False
                report.append(f"t={tf}: no seg channel matched")
                continue
            for i, gids in enumerate(geom_ids):
                px = int(np.isin(vals, [g + 1 for g in gids]).sum())
                if px < 50:
                    all_ok = False
                    report.append(f"t={tf} g{i}: {px}px")
        if all_ok:
            print(f"framing OK at distance={cam.distance:.2f} on frames {sample_ts}")
            break
        print(f"attempt {attempt} failed ({report}); widening")
        cam.distance *= 1.25
    else:
        raise SystemExit("FRAMING FAIL after widening retries")

    writer = imageio.get_writer(args.out, fps=50, macro_block_size=1, quality=8)
    for t in range(T):
        set_pose(t)
        set_cam(t)
        renderer.update_scene(data, camera=cam)
        writer.append_data(renderer.render())
        if t % 100 == 0:
            print(f"  frame {t}/{T}")
    writer.close()
    print(f"wrote {args.out}: {T} frames @50fps ({T / 50:.1f}s)")


if __name__ == "__main__":
    main()
