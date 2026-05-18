# Vortexo IPTV

Vortexo IPTV tracks [matthuisman/i.mjh.nz](https://github.com/matthuisman/i.mjh.nz) and adds an Australia-focused merged IPTV output for IPTV apps.

The goal is simple: one playlist, one EPG, clean groups, Australian local channels preferred, and no New Zealand channels in the merged AU output.

## IPTV App URLs

Use these in IPTV App settings when adding a Live TV source.

### Recommended Playlist

M3U playlist:

```text
https://raw.githubusercontent.com/ZeroQ-bit/Vortexo-IPTV/master/merged/au/raw-tv.m3u8
```

EPG:

```text
https://raw.githubusercontent.com/ZeroQ-bit/Vortexo-IPTV/master/merged/au/epg.xml.gz
```

This is the normal merged list. Regional AU channels are merged together, with Perth/WA preferred by default.
The EPG is published compressed so it can include rich artwork and descriptions without exceeding GitHub file limits.

### Expanded Playlist

M3U playlist:

```text
https://raw.githubusercontent.com/ZeroQ-bit/Vortexo-IPTV/master/merged/au/raw-tv-expanded.m3u8
```

EPG:

```text
https://raw.githubusercontent.com/ZeroQ-bit/Vortexo-IPTV/master/merged/au/epg-expanded.xml.gz
```

Use this if you want every regional variant listed separately, for example 10 WA, 10 NSW, 10 VIC, and so on.

### JSON Catalog

```text
https://raw.githubusercontent.com/ZeroQ-bit/Vortexo-IPTV/master/merged/au/tv.json.gz
```

This is for apps that can understand richer channel data. It includes variants, categories, logos, EPG IDs, source names, and fallback metadata.

## What Is Included

The merged AU output currently includes public/playable streams from:

| Source | Channels |
| --- | ---: |
| PlutoTV | 2401 |
| Samsung TV Plus | 2315 |
| Roku | 363 |
| Plex AU | 291 |
| i.mjh.nz AU | 195 |
| PBS Kids | 1 |

Current generated total:

```text
5566 merged channels
5620 variants
```

Categories are generated into groups such as:

```text
24/7
AU Freeview
Movies
Series
Kids
News
Documentaries
Lifestyle
Sport
Music
Comedy
Entertainment
```

## What We Changed

This fork adds:

- `scripts/build_au_merged.py`
- `merged/au/raw-tv.m3u8`
- `merged/au/raw-tv-expanded.m3u8`
- `merged/au/epg.xml.gz`
- `merged/au/epg-expanded.xml.gz`
- `merged/au/tv.json.gz`
- `merged/au/skipped-sources.json`
- A daily GitHub Actions workflow that syncs from upstream and rebuilds the Vortexo IPTV AU output.

The generator:

- Syncs the latest upstream data.
- Excludes New Zealand channels from the AU merged output.
- Merges Australian regional variants into one default channel.
- Prefers Perth/WA regional streams for the normal playlist.
- Groups explicit 24/7 channels and AU FAST channels into a `24/7` category.
- Remaps rich upstream XMLTV metadata into the merged IDs, including program artwork, descriptions, categories, and subtitles when available.
- Keeps all variants in the expanded playlist and JSON catalog.
- Pulls public SlyGuy-style stream templates where possible, such as `jmp2.uk` redirects for PlutoTV, Roku, Samsung TV Plus, and Plex AU.
- Skips channels that need Widevine DRM, paid provider authentication, or private/local redirect services.

## Skipped Sources

Some folders in upstream are EPG-only or require account login, DRM, or a local service. Those are not placed into the public merged playlist.

See:

```text
merged/au/skipped-sources.json
```

Examples:

- Binge, Foxtel, Kayo: provider auth/DRM or EPG-only.
- DStv: EPG-only here; related upstream repo is unavailable due to takedown.
- MeTV, Singtel, SkyGo, SkySportNow, hgtv_go: EPG/app metadata only or auth-focused.
- PBS main stations: Widevine-protected, so only PBS Kids is included.

## Daily Sync

The workflow is:

```text
.github/workflows/sync-upstream-and-build-au-merge.yml
```

It runs daily and can also be started manually from GitHub Actions. It:

1. Checks out this fork.
2. Fetches and merges `matthuisman/i.mjh.nz`.
3. Rebuilds the merged AU outputs.
4. Commits and pushes changes back to this fork.

## Notes

Vortexo IPTV is not the official upstream project. Original data and provider work come from Matthuisman's i.mjh.nz and related SlyGuy projects.

Some public FAST channels are geo-restricted or may stop working if a provider changes its endpoint. The merged output is best-effort and rebuilt daily.
