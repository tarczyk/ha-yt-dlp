# Containers and codecs per Download Profile are chosen for DLNA playback from Home Assistant

Downloads are played on TVs and streamers that Home Assistant drives over DLNA, and HA hides any file whose type the renderer does not advertise. So the container is chosen for what renders, not for what yt-dlp would pick by default: the MP4 profile is restricted to H.264 + AAC, Best Video is merged into WebM (AV1/VP9 + Opus, MP4 only when the source offers nothing but H.264), and MKV is never produced. Best Audio keeps the source stream untouched (`.opus`, or `.m4a` when the source only has AAC) instead of re-encoding to a more widely accepted format.

## Considered Options

Measured on 2026-11-06 with a Samsung QE65Q80A (2021) and a WiiM Pro, both via HA's DLNA Digital Media Renderer, using 4K clips from YouTube:

| File | Samsung Q80A | WiiM Pro |
|---|---|---|
| H.264 + AAC in MP4 | plays | — |
| AV1 + AAC in MP4 (previous MP4 profile) | rejected (UPnP 701) | — |
| VP9 + Opus in MP4 | rejected | — |
| AV1 + Opus in WebM | plays, with sound | — |
| VP9 + Opus in WebM | plays, with sound | — |
| any codec in MKV | hidden by HA | — |
| Opus in `.opus` / `.ogg` | — | plays |
| AAC in `.m4a` / `.aac` | — | hidden by HA |

- **Let yt-dlp choose the container**: rejected; it falls back to MKV when codecs don't share a container.
- **Always MKV**: rejected; hidden by HA for the Samsung renderer.
- **Best Audio as AAC `.m4a`, or re-encode to MP3 when Opus is missing**: rejected; `.m4a` is hidden for the WiiM anyway, and re-encoding would make Best Audio indistinguishable from the MP3 profile.

## Consequences

- MP4 downloads drop from up to 4K (AV1) to H.264, typically 1080p on YouTube. 4K now comes from Best Video.
- MP4 files must have the index at the start (`+faststart`); clips without it were rejected by the Samsung even with H.264.
- Best Audio from a source that only offers AAC produces a `.m4a` that does not play on the WiiM through HA; the MP3 profile is the fallback.
- The table reflects these two devices only. Revisit if a renderer with different capabilities becomes the main target.
