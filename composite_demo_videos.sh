#!/usr/bin/env bash
# Composite the two demo videos from rendered panels + PIL label bars.
#
# Prereqs (see docs/REPRODUCE.md):
#   eval/assets/input_excerpt_29_37.mp4   input video trimmed to the common window
#   eval/assets/hero_track4_ghost.mp4     render_rollout.py --comparison ghost (640x480)
#   eval/assets/grid_track{1..9}.mp4      render_rollout.py --comparison policy (320x240)
#   eval/assets/label_hero.png            make_label.py, 1494x120
#   eval/assets/label_grid.png            make_label.py, 2240x120
#
# FFMPEG: homebrew ffmpeg lacks drawtext on this Mac, so labels are PIL-rendered
# PNGs stacked with vstack. Default picks the imageio_ffmpeg static build from the
# SuperMimic-MuJoCo venv; override with FFMPEG=/path/to/ffmpeg.
#
# Safety: vstack=shortest=1 AND -t 8.0 — with -loop 1 on a still image, framesync
# filters default to repeating the last frame forever and -shortest alone does NOT
# stop the muxer (learned the hard way: 175MB runaway output).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
A="$ROOT/eval/assets"
FF="${FFMPEG:-$ROOT/../SuperMimic-MuJoCo/.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v9.0}"
[ -x "$FF" ] || FF=ffmpeg

"$FF" -loglevel error -i "$A/input_excerpt_29_37.mp4" -i "$A/hero_track4_ghost.mp4" -loop 1 -i "$A/label_hero.png" \
  -filter_complex "[0:v]fps=30,scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2,setsar=1[l];[1:v]fps=30,setsar=1[r];[2:v]fps=30[lbl];[l][r]hstack=2[v];[lbl][v]vstack=shortest=1[out]" \
  -map "[out]" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -movflags +faststart -t 8.0 -y "$A/demo_hero.mp4"
echo "hero  -> $A/demo_hero.mp4"

"$FF" -loglevel error -i "$A/input_excerpt_29_37.mp4" \
  -i "$A/grid_track1.mp4" -i "$A/grid_track2.mp4" -i "$A/grid_track3.mp4" \
  -i "$A/grid_track4.mp4" -i "$A/grid_track5.mp4" -i "$A/grid_track6.mp4" \
  -i "$A/grid_track7.mp4" -i "$A/grid_track8.mp4" -i "$A/grid_track9.mp4" \
  -loop 1 -i "$A/label_grid.png" \
  -filter_complex "[0:v]fps=30,scale=1280:720,setsar=1[l];[1:v]fps=30,setsar=1[g1];[2:v]fps=30,setsar=1[g2];[3:v]fps=30,setsar=1[g3];[4:v]fps=30,setsar=1[g4];[5:v]fps=30,setsar=1[g5];[6:v]fps=30,setsar=1[g6];[7:v]fps=30,setsar=1[g7];[8:v]fps=30,setsar=1[g8];[9:v]fps=30,setsar=1[g9];[g1][g2][g3]hstack=3[r1];[g4][g5][g6]hstack=3[r2];[g7][g8][g9]hstack=3[r3];[r1][r2][r3]vstack=3[g];[l][g]hstack=2[v];[10:v]fps=30[lbl];[lbl][v]vstack=shortest=1[out]" \
  -map "[out]" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -movflags +faststart -t 8.0 -y "$A/demo_grid.mp4"
echo "grid  -> $A/demo_grid.mp4"

mkdir -p "$ROOT/docs/assets"
cp "$A/demo_hero.mp4" "$A/demo_grid.mp4" "$ROOT/docs/assets/"
echo "published -> docs/assets/{demo_hero,demo_grid}.mp4"
