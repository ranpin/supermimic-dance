#!/usr/bin/env python3
"""Select the best demo excerpt window from SuperMimic evaluation rollouts.

For each rollout.npz, scores every sliding window (default 8 s at the 50 Hz
control rate) on:
- err_deg: mean per-frame joint MAE between policy q and reference ref_q,
  indexed by recorded f_t (same convention as tools/analyze_rollout.py)
- intensity: mean reference joint speed (deg/s) — dance-ness proxy
- alive gate: every step in the window must be alive

Best window = max intensity among windows with err_deg <= median window err
(the best-tracking half of the clip).

Usage: select_excerpt.py OUT.json [--window-sec 8] [--step-sec 0.5] NAME=ROLLOUT.npz ...
"""
import argparse
import json

import numpy as np

HZ = 50.0
SRC_FPS = 30.0


def load(rollout_path):
    d = np.load(rollout_path, allow_pickle=True)
    q = d["q"][:, 0, :].astype(np.float64)
    f = d["f"][:, 0].astype(np.int64)
    alive = d["alive"][:, 0].astype(bool)
    ref_q = d["ref_q"].astype(np.float64)
    return q, f, alive, ref_q


def per_frame(q, f, alive, ref_q):
    err = np.degrees(np.abs(q - ref_q[f]).mean(axis=-1))
    err[~alive] = np.nan
    ref_speed = np.degrees(np.abs(np.diff(ref_q, axis=0)).mean(axis=-1)) * HZ
    return err, ref_speed


def windows(err, ref_speed, f, alive, win, step):
    T = err.shape[0]
    out = []
    for t0 in range(0, max(1, T - win + 1), step):
        t1 = t0 + win
        if not alive[t0:t1].all():
            continue
        idx = np.clip(f[t0:t1], 0, ref_speed.shape[0] - 1)
        out.append({
            "t0": t0, "t1": t1,
            "err_deg": float(np.nanmean(err[t0:t1])),
            "err_max_deg": float(np.nanmax(err[t0:t1])),
            "intensity_deg_s": float(ref_speed[idx].mean()),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_json")
    ap.add_argument("--window-sec", type=float, default=8.0)
    ap.add_argument("--step-sec", type=float, default=0.5)
    ap.add_argument("clips", nargs="+", help="NAME=path/to/rollout.npz")
    args = ap.parse_args()
    win = int(args.window_sec * HZ)
    step = int(args.step_sec * HZ)

    report = {}
    for pair in args.clips:
        name, path = pair.split("=", 1)
        q, f, alive, ref_q = load(path)
        err, ref_speed = per_frame(q, f, alive, ref_q)
        ws = windows(err, ref_speed, f, alive, win, step)
        if not ws:
            report[name] = {"error": "no fully-alive window", "T": int(q.shape[0]),
                            "alive_steps": int(alive.sum())}
            print(f"{name}: NO ALIVE WINDOW (T={q.shape[0]}, alive={alive.sum()})")
            continue
        errs = np.array([w["err_deg"] for w in ws])
        med = float(np.median(errs))
        good = [w for w in ws if w["err_deg"] <= med]
        best = max(good, key=lambda w: w["intensity_deg_s"])
        best["t0_sec"] = best["t0"] / HZ
        best["t1_sec"] = best["t1"] / HZ
        best["src_frame0"] = int(round(best["t0_sec"] * SRC_FPS))
        best["src_frame1"] = int(round(best["t1_sec"] * SRC_FPS))
        report[name] = {
            "clip_mean_err_deg": float(np.nanmean(err)),
            "window_err_median_deg": med,
            "n_windows": len(ws),
            "best": best,
        }
        print(f"{name}: clip_err={np.nanmean(err):.2f}deg win_med={med:.2f}deg "
              f"best=[{best['t0_sec']:.1f}-{best['t1_sec']:.1f}]s "
              f"err={best['err_deg']:.2f}deg max={best['err_max_deg']:.2f}deg "
              f"intensity={best['intensity_deg_s']:.1f}deg/s "
              f"src_frames={best['src_frame0']}-{best['src_frame1']}")
    with open(args.out_json, "w") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
