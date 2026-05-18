#!/usr/bin/env python3
"""Build an Australia-focused merged IPTV catalog from i.mjh.nz data.

The upstream "all" catalog currently contains Australia, New Zealand, and a
small world news set. This generator keeps Australia + world, excludes New
Zealand, and writes both a merged playlist and an expanded playlist that keeps
regional variants available for apps that support fallback selection.
"""

from __future__ import annotations

import gzip
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "merged" / "au"

PRIMARY_SOURCES = [
    ("au/all", ROOT / "au" / "all" / "tv.json.gz"),
    ("world", ROOT / "world" / "tv.json.gz"),
]

OPTIONAL_SOURCES = [
    ("all", ROOT / "all" / "tv.json.gz"),
]

EXCLUDED_SOURCE_FILES = [
    ROOT / "nz" / "tv.json.gz",
]

REGION_SUFFIXES = {
    "act",
    "ade",
    "bri",
    "cns",
    "dar",
    "hob",
    "mel",
    "mky",
    "nsw",
    "nt",
    "per",
    "qld",
    "rky",
    "sa",
    "ssc",
    "syd",
    "tas",
    "tsv",
    "twb",
    "vic",
    "wa",
    "wby",
}

REGION_LABELS = {
    "act": "Canberra",
    "ade": "Adelaide",
    "bri": "Brisbane",
    "cns": "Cairns",
    "dar": "Darwin",
    "hob": "Hobart",
    "mel": "Melbourne",
    "mky": "Mackay",
    "nsw": "New South Wales",
    "nt": "Northern Territory",
    "per": "Perth",
    "qld": "Queensland",
    "rky": "Rockhampton",
    "sa": "South Australia",
    "ssc": "Sunshine Coast",
    "syd": "Sydney",
    "tas": "Tasmania",
    "tsv": "Townsville",
    "twb": "Toowoomba",
    "vic": "Victoria",
    "wa": "Western Australia",
    "wby": "Wide Bay",
}

# Default to Western Australia/Perth for this fork. Apps can still select a
# different region from the expanded playlist or JSON variants.
REGION_PRIORITY = {
    "per": 0,
    "wa": 1,
    "syd": 10,
    "nsw": 11,
    "mel": 20,
    "vic": 21,
    "bri": 30,
    "qld": 31,
    "ade": 40,
    "sa": 41,
    "act": 50,
    "hob": 60,
    "tas": 61,
    "dar": 70,
    "nt": 71,
}


@dataclass
class ChannelVariant:
    source: str
    channel_id: str
    data: dict[str, Any]

    @property
    def epg_id(self) -> str:
        return str(self.data.get("epg_id") or self.channel_id)

    @property
    def name(self) -> str:
        return str(self.data.get("name") or self.channel_id)

    @property
    def url(self) -> str:
        return str(self.data.get("mjh_master") or self.data.get("url") or "")

    @property
    def region(self) -> str:
        return detect_region(self.channel_id)

    @property
    def region_name(self) -> str:
        return REGION_LABELS.get(self.region, self.region.upper() if self.region else "")

    @property
    def chno(self) -> int:
        value = self.data.get("chno")
        try:
            return int(value)
        except (TypeError, ValueError):
            return 99999


def load_json_gz(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not contain a JSON object")
    return data


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as handle:
        handle.write(text)


def detect_region(channel_id: str) -> str:
    match = re.search(r"-([a-z0-9]+)$", channel_id.lower())
    if not match:
        return ""
    suffix = match.group(1)
    return suffix if suffix in REGION_SUFFIXES else ""


def canonical_id(channel_id: str, data: dict[str, Any]) -> str:
    epg_id = str(data.get("epg_id") or channel_id).lower()

    for pattern in [
        r"^(mjh-10(?:bold|peach|shake)?)-(?:nsw|qld|sa|vic|wa)$",
        r"^(mjh-(?:gem|go|life|rush))-(?:nsw|qld|sa|vic|wa)$",
    ]:
        match = re.match(pattern, epg_id)
        if match:
            return match.group(1)

    match = re.match(r"^mjh-abc-(?:act|nsw|nt|qld|sa|tas|vic|wa)$", epg_id)
    if match:
        return "mjh-abc-tv"

    match = re.match(r"^mjh-channel-9-(?:nsw|qld|sa|vic|wa)$", epg_id)
    if match:
        return "mjh-channel-9"

    match = re.match(
        r"^mjh-seven-(?:syd|mel|bri|ade|per|cns|mky|rky|ssc|tsv|twb|wby)$",
        epg_id,
    )
    if match:
        return "mjh-seven"

    return epg_id


def category_for(variant: ChannelVariant) -> str:
    name = variant.name.lower()
    network = str(variant.data.get("network") or "").lower()
    group = str(variant.data.get("group") or "").lower()
    text = f"{name} {network} {group}"

    if name in {"10", "seven", "channel 9", "abc tv", "sbs"}:
        return "AU Freeview"
    if any(word in text for word in ["news", "al jazeera", "dw", "euronews", "france 24"]):
        return "News"
    if any(word in text for word in ["kid", "junior", "nick", "cartoon", "spongebob"]):
        return "Kids"
    if any(word in text for word in ["movie", "movies", "cinema", "romance"]):
        return "Movies"
    if any(word in text for word in ["documentary", "history", "nature", "predator", "h2"]):
        return "Documentaries"
    if "sport" in text:
        return "Sport"
    if any(word in text for word in ["music", "radio", "chill", "popasia"]):
        return "Music"
    if any(word in text for word in ["food", "cook", "home", "garden", "house", "hgtv", "travel"]):
        return "Lifestyle"
    if any(word in text for word in ["comedy", "animation", "sitcom"]):
        return "Comedy"
    if any(word in text for word in ["drama", "series", "show", "entertain", "reality"]):
        return "Series"
    if network in {"abc", "sbs", "seven", "nine", "ten"}:
        return "AU Freeview"
    return "Entertainment"


def variant_sort_key(variant: ChannelVariant) -> tuple[int, int, str]:
    region_score = REGION_PRIORITY.get(variant.region, 500)
    source_score = 0 if variant.source == "au/all" else 100
    return (region_score, source_score, variant.name.lower())


def channel_sort_key(item: tuple[str, list[ChannelVariant]]) -> tuple[int, str]:
    _, variants = item
    primary = choose_primary(variants)
    return (primary.chno, primary.name.lower())


def choose_primary(variants: list[ChannelVariant]) -> ChannelVariant:
    return sorted(variants, key=variant_sort_key)[0]


def load_excluded_ids() -> set[str]:
    excluded: set[str] = set()
    for path in EXCLUDED_SOURCE_FILES:
        for key, value in load_json_gz(path).items():
            if isinstance(value, dict):
                excluded.add(str(value.get("epg_id") or key).lower())
            excluded.add(str(key).lower())
    return excluded


def collect_channels() -> dict[str, list[ChannelVariant]]:
    excluded = load_excluded_ids()
    buckets: dict[str, list[ChannelVariant]] = {}

    def add_source(source: str, path: Path, skip_existing: bool) -> None:
        for channel_id, data in load_json_gz(path).items():
            if not isinstance(data, dict):
                continue
            epg_id = str(data.get("epg_id") or channel_id).lower()
            if epg_id in excluded or str(channel_id).lower() in excluded:
                continue
            if not data.get("mjh_master") and not data.get("url"):
                continue
            key = canonical_id(str(channel_id), data)
            if skip_existing and key in buckets:
                continue
            buckets.setdefault(key, []).append(ChannelVariant(source, str(channel_id), data))

    for source, path in PRIMARY_SOURCES:
        add_source(source, path, skip_existing=False)
    for source, path in OPTIONAL_SOURCES:
        add_source(source, path, skip_existing=True)

    return buckets


def build_json_catalog(buckets: dict[str, list[ChannelVariant]]) -> dict[str, Any]:
    catalog: dict[str, Any] = {}
    for merged_id, variants in sorted(buckets.items(), key=channel_sort_key):
        primary = choose_primary(variants)
        payload = dict(primary.data)
        payload["epg_id"] = merged_id
        payload["source"] = primary.source
        payload["category"] = category_for(primary)
        if primary.region:
            payload["region"] = primary.region_name
        payload["mjh_master"] = primary.url
        payload["variants"] = [
            {
                "source": variant.source,
                "channel_id": variant.channel_id,
                "epg_id": variant.epg_id,
                "name": variant.name,
                "region": variant.region_name,
                "mjh_master": variant.url,
                "logo": variant.data.get("logo"),
                "network": variant.data.get("network"),
                "category": category_for(variant),
            }
            for variant in sorted(variants, key=variant_sort_key)
        ]
        catalog[merged_id] = payload
    return catalog


def extinf(variant: ChannelVariant, channel_id: str, tvg_id: str, name: str) -> str:
    attrs = {
        "channel-id": channel_id,
        "tvg-id": tvg_id,
        "tvg-name": name,
        "tvg-logo": str(variant.data.get("logo") or ""),
        "group-title": category_for(variant),
    }
    if variant.chno != 99999:
        attrs["tvg-chno"] = str(variant.chno)
    attr_text = " ".join(
        f'{key}="{html.escape(value, quote=True)}"'
        for key, value in attrs.items()
        if value
    )
    return f"#EXTINF:-1 {attr_text},{name}\n{variant.url}"


def build_playlist(buckets: dict[str, list[ChannelVariant]], expanded: bool) -> str:
    epg_name = "epg-expanded.xml.gz" if expanded else "epg.xml.gz"
    lines = [f'#EXTM3U x-tvg-url="{epg_name}"', ""]
    for merged_id, variants in sorted(buckets.items(), key=channel_sort_key):
        primary = choose_primary(variants)
        if expanded:
            for variant in sorted(variants, key=variant_sort_key):
                display_name = variant.name
                if variant.region_name:
                    display_name = f"{display_name} ({variant.region_name})"
                lines.append(extinf(variant, variant.epg_id, variant.epg_id, display_name))
                lines.append("")
        else:
            lines.append(extinf(primary, merged_id, merged_id, primary.name))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def xml_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y%m%d%H%M%S +0000")


def write_xmltv_channel(lines: list[str], channel_id: str, variant: ChannelVariant, display_name: str) -> None:
    lines.append(f'  <channel id="{html.escape(channel_id, quote=True)}">')
    lines.append(f"    <display-name>{html.escape(display_name)}</display-name>")
    logo = str(variant.data.get("logo") or "")
    if logo:
        lines.append(f'    <icon src="{html.escape(logo, quote=True)}" />')
    lines.append("  </channel>")


def write_xmltv_programs(lines: list[str], channel_id: str, programs: list[Any]) -> None:
    normalized: list[tuple[int, str]] = []
    for entry in programs:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        try:
            start = int(entry[0])
        except (TypeError, ValueError):
            continue
        title = str(entry[1])
        normalized.append((start, title))

    normalized.sort()
    for index, (start, title) in enumerate(normalized):
        stop = normalized[index + 1][0] if index + 1 < len(normalized) else start + 1800
        if stop <= start:
            stop = start + 1800
        lines.append(
            f'  <programme start="{xml_time(start)}" stop="{xml_time(stop)}" '
            f'channel="{html.escape(channel_id, quote=True)}">'
        )
        lines.append(f"    <title>{html.escape(title)}</title>")
        lines.append("  </programme>")


def build_xmltv(buckets: dict[str, list[ChannelVariant]], expanded: bool) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S +0000")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<tv generator-info-name="ZeroQ AU merged" generated-ts="{generated}">',
    ]

    channels: list[tuple[str, ChannelVariant, str]] = []
    for merged_id, variants in sorted(buckets.items(), key=channel_sort_key):
        primary = choose_primary(variants)
        if expanded:
            for variant in sorted(variants, key=variant_sort_key):
                display_name = variant.name
                if variant.region_name:
                    display_name = f"{display_name} ({variant.region_name})"
                channels.append((variant.epg_id, variant, display_name))
        else:
            channels.append((merged_id, primary, primary.name))

    for channel_id, variant, display_name in channels:
        write_xmltv_channel(lines, channel_id, variant, display_name)

    for channel_id, variant, _ in channels:
        programs = variant.data.get("programs")
        if isinstance(programs, list):
            write_xmltv_programs(lines, channel_id, programs)

    lines.append("</tv>")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    buckets = collect_channels()
    catalog = build_json_catalog(buckets)

    json_text = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (OUTPUT / "tv.json").write_text(json_text, encoding="utf-8")
    write_gzip(OUTPUT / "tv.json.gz", json_text)

    playlist = build_playlist(buckets, expanded=False)
    (OUTPUT / "raw-tv.m3u8").write_text(playlist, encoding="utf-8")

    expanded_playlist = build_playlist(buckets, expanded=True)
    (OUTPUT / "raw-tv-expanded.m3u8").write_text(expanded_playlist, encoding="utf-8")

    xmltv = build_xmltv(buckets, expanded=False)
    (OUTPUT / "epg.xml").write_text(xmltv, encoding="utf-8")
    write_gzip(OUTPUT / "epg.xml.gz", xmltv)

    expanded_xmltv = build_xmltv(buckets, expanded=True)
    (OUTPUT / "epg-expanded.xml").write_text(expanded_xmltv, encoding="utf-8")
    write_gzip(OUTPUT / "epg-expanded.xml.gz", expanded_xmltv)

    variant_count = sum(len(variants) for variants in buckets.values())
    print(f"Wrote {len(buckets)} merged channels with {variant_count} variants to {OUTPUT}")


if __name__ == "__main__":
    main()
