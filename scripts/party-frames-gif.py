"""Crop the owner's live recording; cover names and exclude cursor-heavy cuts."""
from pathlib import Path
import argparse
import subprocess

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('--ffmpeg', required=True)
args = parser.parse_args()
out = root / 'docs/images/priestshieldtracker-party-frames.gif'
# First 20 seconds: application, active icon, swipe and removal. The cursor
# remains outside this crop. Opaque masks remove both character name rows.
filters = ('fps=10,crop=176:138:532:226,'
    'drawbox=x=6:y=3:w=140:h=20:color=0x24242b:t=fill,'
    'drawbox=x=6:y=68:w=140:h=20:color=0x24242b:t=fill,'
    'scale=528:414:flags=neighbor,split[a][b];'
    '[a]palettegen=max_colors=128:stats_mode=diff[p];'
    '[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle')
subprocess.run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
    '-i', args.source, '-t', '20', '-filter_complex', filters, '-an', '-loop', '0', str(out)], check=True)
print(f'{out}: {out.stat().st_size:,} bytes')
