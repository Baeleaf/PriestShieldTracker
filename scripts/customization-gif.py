"""Build a cursor-free showcase from the owner's November 14 OBS recording.

Requires FFmpeg and Windows System.Drawing. Cuts retain original animation speed.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STAGES = [
    dict(start=0.10, duration=1.10, style="Classic", palette="Soul", accent="#b58af0"),
    dict(start=4.20, duration=2.20, style="Smooth", palette="Soul", accent="#b58af0"),
    dict(start=8.00, duration=2.20, style="Smooth", palette="Frost", accent="#73d7f6"),
    dict(start=14.25, duration=1.75, style="Smooth", palette="Ember", accent="#f7ad58"),
    dict(start=18.20, duration=2.80, style="Liquid", palette="Ember", accent="#f7ad58"),
    dict(start=24.00, duration=2.25, style="Liquid", palette="Void", accent="#cc99fa"),
]


def build(source, ffmpeg):
    work = ROOT / ".local/customization-media"
    work.mkdir(parents=True, exist_ok=True)
    manifest = work / "cuts.json"
    manifest.write_text(json.dumps(STAGES, indent=2))
    drawing = (ROOT / "scripts/customization-backgrounds.ps1").read_text().split("\n", 1)[1]
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    drawing = f"$OutputDirectory = {quote(work)}\n$StagesPath = {quote(manifest)}\n" + drawing
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", drawing], check=True)
    def run(args):
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)
    for index, stage in enumerate(STAGES):
        # Only the preview rectangle is retained: menus are lower, the white
        # cursor is outside this rectangle throughout each selected interval.
        graph = ("[0:v]crop=434:92:735:297,scale=640:136:flags=lanczos,fps=12,setpts=PTS-STARTPTS[v];"
            "[1:v][v]overlay=20:60,format=rgb24[out]")
        run(["-ss", str(stage["start"]), "-t", str(stage["duration"]), "-i", str(source),
            "-framerate", "12", "-loop", "1", "-i", str(work / f"background-{index}.png"), "-filter_complex", graph,
            "-map", "[out]", "-an", "-t", str(stage["duration"]), "-c:v", "ffv1", str(work / f"stage-{index}.mkv")])
    concat = work / "segments.txt"
    concat.write_text("".join(f"file 'stage-{i}.mkv'\n" for i in range(len(STAGES))))
    output = ROOT / "docs/images/priestshieldtracker-customization.gif"
    run(["-f", "concat", "-safe", "0", "-i", str(concat), "-filter_complex",
        "split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
        "-loop", "0", str(output)])
    run(["-i", str(output), "-vf", "fps=1/2,tile=3x3:padding=8:margin=8:color=black",
        "-frames:v", "1", "-update", "1", str(work / "gif-review.jpg")])
    print(f"{output}\n{output.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error("Supply --ffmpeg with an installed FFmpeg executable")
    build(args.source, args.ffmpeg)
