"""Data sources: demo data, YouTube Studio CSV exports, and the YouTube Data API.

Every loader returns a DataFrame in one normalized shape:

    video_id, title, published, duration_sec, views, likes, comments,
    [shares, impressions, ctr, avg_view_pct, avg_view_sec, subs_gained,
     thumbnail, <any custom tag columns>]

Optional columns may be missing or NaN; the engine only uses what it has.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

CORE_NUMERIC = ["duration_sec", "views", "likes", "comments"]
OPTIONAL_NUMERIC = [
    "shares", "impressions", "ctr", "avg_view_pct", "avg_view_sec", "subs_gained",
]
KNOWN_COLUMNS = {"video_id", "title", "published", "thumbnail", *CORE_NUMERIC, *OPTIONAL_NUMERIC}

# Column aliases, matched case-insensitively after stripping punctuation.
# Covers YouTube Studio "Advanced mode -> Export -> Table data.csv" plus common hand-made sheets.
ALIASES = {
    "video_id": ["content", "video id", "videoid", "id", "video"],
    "title": ["video title", "title", "name"],
    "published": ["video publish time", "publish time", "published", "publish date", "date", "upload date"],
    "duration_sec": ["duration", "duration sec", "length", "duration seconds"],
    "views": ["views", "view count"],
    "likes": ["likes", "like count"],
    "comments": ["comments added", "comments", "comment count"],
    "shares": ["shares"],
    "impressions": ["impressions"],
    "ctr": ["impressions click through rate", "impressions ctr", "ctr", "click through rate"],
    "avg_view_pct": ["average percentage viewed", "avg percentage viewed", "avg view pct", "retention"],
    "avg_view_sec": ["average view duration", "avg view duration", "avd"],
    "subs_gained": ["subscribers gained", "subscribers", "subs gained", "subs"],
    "thumbnail": ["thumbnail", "thumbnail url"],
}


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"[_\-]", " ", str(s).lower())).strip()


def _to_seconds(v) -> float:
    """Accept 754, '754', '12:34', '1:02:03', or ISO-8601 'PT12M34S'."""
    if pd.isna(v):
        return np.nan
    if isinstance(v, (int, float, np.number)):
        return float(v)
    s = str(v).strip()
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if m and s.startswith("P"):
        d, h, mi, se = (int(x or 0) for x in m.groups())
        return float(d * 86400 + h * 3600 + mi * 60 + se)
    if ":" in s:
        total = 0.0
        for part in s.split(":"):
            total = total * 60 + float(part or 0)
        return total
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return np.nan


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Map arbitrary column names onto the normalized schema; keep unknown text columns as tags."""
    lookup = {_key(c): c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    used = set()
    for target, names in ALIASES.items():
        for n in names:
            if n in lookup and lookup[n] not in used:
                out[target] = df[lookup[n]]
                used.add(lookup[n])
                break

    if "title" not in out and "video_id" in out:
        out["title"] = out["video_id"]
    if "video_id" not in out:
        out["video_id"] = out.get("title", pd.Series(range(len(df)), index=df.index)).astype(str)
    if "views" not in out:
        raise ValueError("Couldn't find a 'Views' column. Check the CSV has a header row with Views in it.")

    # Drop YouTube Studio's "Total" summary row.
    out = out[~out["video_id"].astype(str).str.strip().str.lower().isin(["total", ""])]
    df = df.loc[out.index]

    for c in ["duration_sec", "avg_view_sec"]:
        if c in out:
            out[c] = out[c].map(_to_seconds)
    for c in CORE_NUMERIC + OPTIONAL_NUMERIC:
        if c in out and c not in ("duration_sec", "avg_view_sec"):
            out[c] = pd.to_numeric(out[c].astype(str).str.replace(r"[,%]", "", regex=True), errors="coerce")
        elif c not in out and c in CORE_NUMERIC:
            out[c] = np.nan

    if "published" in out:
        out["published"] = pd.to_datetime(out["published"], errors="coerce", utc=True, format="mixed")
    else:
        out["published"] = pd.NaT

    # Derive retention % if only average view duration is present.
    if "avg_view_pct" not in out and "avg_view_sec" in out:
        out["avg_view_pct"] = 100 * out["avg_view_sec"] / out["duration_sec"]

    # Any leftover low-cardinality text column is a creator-defined content tag.
    for c in df.columns:
        if c in used or _key(c) in ("watch time hours",):
            continue
        col = df[c]
        if not pd.api.types.is_numeric_dtype(col) and 1 < col.nunique() <= max(12, len(col) // 3):
            out[f"tag:{c.strip()}"] = col.astype(str).str.strip()

    out["title"] = out["title"].astype(str)
    out["video_id"] = out["video_id"].astype(str).str.strip()
    return out.reset_index(drop=True)


def load_csv(file) -> pd.DataFrame:
    raw = file.read() if hasattr(file, "read") else open(file, "rb").read()
    text = raw.decode("utf-8-sig", errors="replace")
    return normalize(pd.read_csv(io.StringIO(text)))


def enrich(base: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    """Merge a Studio CSV (CTR, retention, subs, tags) into API data on video_id."""
    extra = extra.drop(columns=[c for c in ("title", "published", "thumbnail") if c in extra])
    merged = base.merge(extra, on="video_id", how="left", suffixes=("", "_csv"))
    for c in list(merged.columns):
        if c.endswith("_csv"):
            orig = c[:-4]
            merged[orig] = merged[orig].where(merged[orig].notna(), merged[c])
            merged = merged.drop(columns=c)
    return merged


# --------------------------------------------------------------------------- YouTube Data API

API = "https://www.googleapis.com/youtube/v3"


def _get(path: str, key: str, **params) -> dict:
    r = requests.get(f"{API}/{path}", params={**params, "key": key}, timeout=20)
    if r.status_code != 200:
        try:
            msg = r.json()["error"]["message"]
        except Exception:
            msg = r.text[:200]
        raise RuntimeError(f"YouTube API error ({r.status_code}): {msg}")
    return r.json()


def fetch_channel(channel: str, api_key: str, max_videos: int = 200) -> tuple[pd.DataFrame, dict]:
    """Pull public stats for a channel's uploads. `channel` is @handle, channel ID, or URL."""
    channel = channel.strip().rstrip("/")
    m = re.search(r"(@[\w.\-]+)|(UC[\w\-]{22})", channel)
    ident = m.group(0) if m else channel
    params = {"part": "snippet,statistics,contentDetails"}
    if ident.startswith("UC"):
        params["id"] = ident
    else:
        params["forHandle"] = ident if ident.startswith("@") else "@" + ident
    data = _get("channels", api_key, **params)
    if not data.get("items"):
        raise RuntimeError(f"No channel found for '{channel}'.")
    ch = data["items"][0]
    info = {
        "name": ch["snippet"]["title"],
        "subscribers": int(ch["statistics"].get("subscriberCount", 0)),
        "total_views": int(ch["statistics"].get("viewCount", 0)),
        "thumbnail": ch["snippet"]["thumbnails"].get("default", {}).get("url"),
    }
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token = [], None
    while len(ids) < max_videos:
        page = _get("playlistItems", api_key, part="contentDetails", playlistId=uploads,
                    maxResults=50, **({"pageToken": token} if token else {}))
        ids += [it["contentDetails"]["videoId"] for it in page.get("items", [])]
        token = page.get("nextPageToken")
        if not token:
            break
    ids = ids[:max_videos]

    rows = []
    for i in range(0, len(ids), 50):
        batch = _get("videos", api_key, part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
        for v in batch.get("items", []):
            st, sn = v.get("statistics", {}), v["snippet"]
            thumbs = sn.get("thumbnails", {})
            rows.append({
                "video_id": v["id"],
                "title": sn["title"],
                "published": sn["publishedAt"],
                "duration_sec": _to_seconds(v["contentDetails"]["duration"]),
                "views": int(st.get("viewCount", 0)),
                "likes": float(st["likeCount"]) if "likeCount" in st else np.nan,
                "comments": float(st["commentCount"]) if "commentCount" in st else np.nan,
                "thumbnail": (thumbs.get("medium") or thumbs.get("default") or {}).get("url"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Channel has no public uploads.")
    df["published"] = pd.to_datetime(df["published"], utc=True)
    return df, info


# --------------------------------------------------------------------------- demo data

_STORIES = {
    "Revenge": ["The Groom Who Planned His Own Funeral", "She Waited 20 Years To Make Him Pay",
                "My Brother Burned Everything I Loved", "The Butler Knew What They Did",
                "He Poisoned The Whole Village", "The Debt That Was Paid In Blood"],
    "Mystery": ["Nobody Can Explain What Happened In Room 9", "The Lighthouse Keeper Vanished",
                "Why Did 40 People Walk Into The Sea?", "The Letter Arrived 30 Years Late",
                "What Was Buried Under The Chapel?", "The Town That Erased One Day"],
    "Supernatural": ["Something Followed Us Home From The Woods", "The Doll That Remembered",
                     "Don't Answer If It Knocks Three Times", "The Mirror Showed Her Death",
                     "It Speaks Through The Radio At 3AM", "The Child Who Wasn't There"],
    "Tragedy": ["The Last Letter He Never Sent", "She Lost Everything In One Night",
                "The Soldier Who Came Home Wrong", "A Father's Final Choice",
                "The Fire That Took Our Street", "Goodbye, Little Sparrow"],
    "Survival": ["7 Days Trapped Under The Ice", "Lost In The Desert With No Water",
                 "The Mine Collapsed And We Were Still Inside", "Hunted Across The Frozen Pass",
                 "Adrift: 76 Days On A Broken Raft", "The Cave Swallowed Our Only Rope"],
}


def demo_data(n: int = 64, seed: int = 7) -> tuple[pd.DataFrame, dict]:
    """A realistic dark-storytelling channel with planted patterns the engine should find."""
    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc)
    effects = {
        "story": {"Revenge": 0.45, "Mystery": 0.25, "Supernatural": 0.05, "Tragedy": -0.35, "Survival": 0.1},
        "visual": {"Cinematic AI art": 0.3, "Hand-drawn animation": 0.4, "Stock footage": -0.35, "Narrator on camera": -0.1},
        "hook": {"Cold open": 0.35, "Flash-forward": 0.25, "Question": 0.0, "Narrator intro": -0.4},
    }
    retention_fx = {"Hand-drawn animation": 8, "Cinematic AI art": 4, "Stock footage": -9, "Narrator on camera": -2,
                    "Cold open": 6, "Flash-forward": 4, "Question": 0, "Narrator intro": -10}
    rows, used = [], {k: 0 for k in _STORIES}
    gaps = rng.choice([2, 3, 4, 7, 10], size=n, p=[.2, .3, .25, .15, .1])
    days_ago = (gaps[::-1].cumsum()[::-1] - gaps[-1] + 3).astype(float)  # newest upload is 3 days old
    for i in range(n):
        story = rng.choice(list(_STORIES))
        title = _STORIES[story][used[story] % 6]
        if used[story] >= 6:
            title += f" (Part {used[story] // 6 + 1})"
        used[story] += 1
        visual = rng.choice(list(effects["visual"]), p=[.35, .2, .3, .15] if i > 20 else [.15, .1, .5, .25])
        hook = rng.choice(list(effects["hook"]), p=[.35, .25, .2, .2] if i > 30 else [.15, .2, .25, .4])
        short = rng.random() < 0.18
        dur = rng.integers(35, 59) if short else int(rng.normal(14, 5) * 60).__abs__() + 240
        growth = 0.012 * i  # channel slowly growing
        quality = effects["story"][story] + effects["visual"][visual] + effects["hook"][hook] + rng.normal(0, .35)
        if dur > 25 * 60:
            quality -= 0.2
        published = now - timedelta(days=float(days_ago[i]))
        age = max((now - published).days, 1)
        base = 4000 * (1 + growth) * (1 - np.exp(-age / 9)) * (1.9 if short else 1)
        views = int(base * np.exp(quality * 1.1 + rng.normal(0, .25)))
        ctr = float(np.clip(5.2 + quality * 2.2 + rng.normal(0, .6) - (1.5 if visual == "Stock footage" else 0), 1, 16))
        ret = float(np.clip((72 if short else 41) + retention_fx[visual] + retention_fx[hook] + rng.normal(0, 4)
                            - max(0, dur / 60 - 15) * 0.8, 8, 98))
        rows.append({
            "video_id": f"demo{i:03d}", "title": title, "published": published, "duration_sec": int(dur),
            "views": views, "likes": int(views * np.clip(rng.normal(.042 + quality * .008, .006), .005, .12)),
            "comments": int(views * np.clip(rng.normal(.006 + (.004 if story in ("Mystery", "Supernatural") else 0), .002), 0, .05)),
            "shares": int(views * np.clip(rng.normal(.004 + quality * .002, .001), 0, .03)),
            "impressions": int(views / (ctr / 100) * rng.uniform(.8, 1.0)), "ctr": round(ctr, 1),
            "avg_view_pct": round(ret, 1), "avg_view_sec": round(dur * ret / 100),
            "subs_gained": int(views * np.clip(rng.normal(.006 + quality * .003, .002), 0, .05)),
            "tag:Story type": story, "tag:Visual style": visual, "tag:Hook": hook,
        })
    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], utc=True)
    info = {"name": "Demo: Midnight Chronicles", "subscribers": 18400, "total_views": int(df.views.sum()),
            "thumbnail": None}
    return df, info
