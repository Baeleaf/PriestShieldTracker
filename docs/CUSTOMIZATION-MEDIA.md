# Customization GIF

Source: the owner's OBS recording `2026-11-14 21-01-23.mp4`, supplied November 14, 2026.

Deliverable: `docs/images/soulshield-customization.gif`, 680 by 230 pixels,
12 fps, 12.25 seconds, 816,150 bytes, looping.

Only the native preview rectangle is retained. The white circle cursor is
outside this crop during all selected intervals. Dropdowns, unrelated gameplay,
chat, other addons, and audio are removed. A title identifies the actual style
and palette in each clip. The footer identifies the AddOns settings location
and sample values. Motion remains at the recording's original speed.

| Source start | Duration | Style | Palette |
| --- | --- | --- | --- |
| 00:00.10 | 1.10 s | Classic | Soul |
| 00:04.20 | 2.20 s | Smooth | Soul |
| 00:08.00 | 2.20 s | Smooth | Frost |
| 00:14.25 | 1.75 s | Smooth | Ember |
| 00:18.20 | 2.80 s | Liquid | Ember |
| 00:24.00 | 2.25 s | Liquid | Void |

The recording demonstrates all three styles and four of the six available
palettes. Holy and Emerald are available in settings but do not appear in this
recording. No missing combinations have been synthesized.

Rebuild using `python scripts/customization-gif.py PATH_TO_SOURCE --ffmpeg PATH_TO_FFMPEG`.
The helper renders title cards through Windows System.Drawing and uses FFmpeg
for accurate cuts, cropping, scaling, and GIF encoding.

The approved GIF and customization section are published in the public GitHub
README, marked as the next update while 0.2.4 is awaiting approval. The GIF's
public main-branch URL is available for CurseForge. The matching CurseForge
section remains prepared locally for the appearance release; remove the
next-update notice from both descriptions when that release is published.
No new tag or release has been created for this documentation update.
