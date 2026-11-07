#!/usr/bin/env bash
# Composite the two demo videos from rendered panels + PIL label bars.
#
# Prereqs (see docs/REPRODUCE.md):
#   eval/assets/input_excerpt_29_37.mp4   input video trimmed to the common window
#   eval/assets/hero_track4_ghost.mp4     render_rollout.py --comparison ghost (640x480)
#   eval/assets/formation_raw.mp4         render_formation.py (960x540, 9-robot single scene)
#   eval/assets/label_hero.png            make_label.py, 1494x120
#   eval/assets/label_formation.png       make_label.py, 1920x120
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

# hero: input excerpt | ghost comparison, label bar on top
"$FF" -loglevel error -i "$A/input_excerpt_29_37.mp4" -i "$A/hero_track4_ghost.mp4" -loop 1 -i "$A/label_hero.png" \
  -filter_complex "[0:v]fps=30,scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2,setsar=1[l];[1:v]fps=30,setsar=1[r];[2:v]fps=30[lbl];[l][r]hstack=2[v];[lbl][v]vstack=shortest=1[out]" \
  -map "[out]" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -movflags +faststart -t 8.0 -y "$A/demo_hero.mp4"
echo "hero      -> $A/demo_hero.mp4"

# formation: input excerpt | 9-robot single-scene replay, label bar on top
"$FF" -loglevel error -i "$A/input_excerpt_29_37.mp4" -i "$A/formation_raw.mp4" -loop 1 -i "$A/label_formation.png" \
  -filter_complex "[0:v]fps=30,scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1[l];[1:v]fps=30,setsar=1[r];[2:v]fps=30[lbl];[l][r]hstack=2[v];[lbl][v]vstack=shortest=1[out]" \
  -map "[out]" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -movflags +faststart -t 8.0 -y "$A/demo_formation.mp4"
echo "formation -> $A/demo_formation.mp4"

mkdir -p "$ROOT/docs/assets"
cp "$A/demo_hero.mp4" "$A/demo_formation.mp4" "$ROOT/docs/assets/"
echo "published -> docs/assets/{demo_hero,demo_formation}.mp4"
