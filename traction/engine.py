"""The Traction engine.

1. Score every video 0-100 against the channel's own baseline (not against YouTube at large),
   adjusting views for video age so a 3-day-old upload isn't punished next to a 6-month-old one.
2. Break each video into "content points" (story theme, hook, visual style, length, timing,
   title craft...) and measure how much each point lifts or drags the score.
3. Diagnose each video: is the problem packaging (people don't click) or payoff (people don't stay)?
4. Turn all of that into a plain-language playbook.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Signal -> (label, weight, what it tells the creator)
SIGNALS = {
    "z_reach":     ("Reach",       0.35, "Views vs what a video of this age normally gets on this channel"),
    "z_retention": ("Retention",   0.25, "Average % of the video watched"),
    "z_engage":    ("Engagement",  0.15, "Likes, comments and shares per view"),
    "z_ctr":       ("Click-through", 0.15, "Impressions click-through rate (thumbnail + title pull)"),
    "z_convert":   ("Conversion",  0.10, "Subscribers gained per 1,000 views"),
}

TIERS = [(75, "Breakout"), (60, "Strong"), (40, "Steady"), (-1, "Underperforming")]

# Lexicon for dark / intense storytelling titles.
THEMES = {
    "Revenge / betrayal": r"reveng|betray|pay(s|ed)? for|debt|poison|traitor|backstab|planned",
    "Mystery / unsolved": r"myster|unsolved|vanish|disappear|nobody (can|knows)|what (was|happened)|secret|explain|missing",
    "Supernatural / horror": r"ghost|haunt|demon|curse|mirror|doll|knock|3 ?am|followed|possess|something|it speaks|wasn.t there",
    "Crime / murder": r"murder|kill|blood|crime|body|serial|detective|police",
    "Tragedy / loss": r"last|lost|goodbye|final|grief|funeral|never sent|tragic|fire|wrong",
    "Survival / peril": r"trapped|surviv|adrift|lost in|hunted|collapse|days|no water|frozen|swallow",
    "Family / relationships": r"father|mother|brother|sister|son|daughter|wife|husband|child|groom|bride",
}


def tier_of(score: float) -> str:
    return next(name for cut, name in TIERS if score >= cut)


def _robust_z(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    med = s.median()
    mad = (s - med).abs().median() * 1.4826
    if not np.isfinite(mad) or mad == 0:
        sd = s.std()
        mad = sd if sd and np.isfinite(sd) else 1.0
    return ((s - med) / mad).clip(-3, 3)


def _usable(s: pd.Series | None, min_n: int = 3) -> bool:
    return s is not None and s.notna().sum() >= min_n and s.nunique(dropna=True) > 1


# --------------------------------------------------------------------------- scoring

def score(df: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    df = df.copy()
    now = now or pd.Timestamp.now(tz="UTC")
    df["age_days"] = ((now - df["published"]).dt.total_seconds() / 86400).clip(lower=0.5)
    df["age_days"] = df["age_days"].fillna(df["age_days"].median() if df["age_days"].notna().any() else 30)
    views = df["views"].fillna(0).clip(lower=0)
    logv = np.log1p(views)

    # Age-adjusted reach. Most views arrive in a video's first couple of weeks, so model the
    # expected views as a saturating curve of age: log(views) ~ a + b * log(1 - e^(-age/7)).
    ramp = np.log(1 - np.exp(-df["age_days"] / 7))
    if len(df) >= 6 and ramp.nunique() > 2 and ramp.std() > 0.05:
        b, _ = np.polyfit(ramp, logv, 1)
        b = float(np.clip(b, 0, 1.5))
    else:
        b = 1.0
    a = float(np.median(logv - b * ramp))
    df["expected_views"] = np.expm1(a + b * ramp)
    df["reach_resid"] = logv - (a + b * ramp)
    df["reach_x"] = np.exp(df["reach_resid"])  # 1.8 = "1.8x the views we'd expect"
    df["z_reach"] = _robust_z(df["reach_resid"])

    safe_views = views.replace(0, np.nan)
    eng = df["likes"].fillna(0) + 2 * df["comments"].fillna(0) + 3 * df.get("shares", pd.Series(0, index=df.index)).fillna(0)
    df["engagement_rate"] = 100 * eng / safe_views
    if _usable(df["likes"]) or _usable(df["comments"]):
        df["z_engage"] = _robust_z(df["engagement_rate"])

    if _usable(df.get("avg_view_pct")):
        # Shorts naturally retain higher - compare within format.
        is_short = df["duration_sec"].fillna(600) <= 60
        z = pd.Series(np.nan, index=df.index)
        for mask in (is_short, ~is_short):
            if mask.sum() >= 3:
                z[mask] = _robust_z(df.loc[mask, "avg_view_pct"])
            elif mask.any():
                z[mask] = 0.0
        df["z_retention"] = z
    if _usable(df.get("ctr")):
        df["z_ctr"] = _robust_z(df["ctr"])
    if _usable(df.get("subs_gained")):
        df["subs_per_1k"] = 1000 * df["subs_gained"] / safe_views
        df["z_convert"] = _robust_z(df["subs_per_1k"])

    active = [k for k in SIGNALS if k in df]
    w = pd.Series({k: SIGNALS[k][1] for k in active})
    zs = df[active]
    weights = zs.notna().mul(w, axis=1)
    composite = zs.fillna(0).mul(w, axis=1).sum(axis=1) / weights.sum(axis=1).replace(0, np.nan)
    df["traction"] = (50 + 18 * composite.fillna(0)).clip(0, 100).round(1)
    df["tier"] = df["traction"].map(tier_of)
    df.attrs["signals"] = active
    return add_features(df)


# --------------------------------------------------------------------------- content points

def _length_bucket(sec: float) -> str:
    if pd.isna(sec):
        return "Unknown"
    m = sec / 60
    if sec <= 60:
        return "Short (≤60s)"
    if m < 5:
        return "1–5 min"
    if m < 10:
        return "5–10 min"
    if m < 20:
        return "10–20 min"
    return "20+ min"


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    t = df["title"].fillna("")
    feats = {}
    feats["Length"] = df["duration_sec"].map(_length_bucket)
    if df["published"].notna().any():
        feats["Publish day"] = df["published"].dt.day_name().fillna("Unknown")
        h = df["published"].dt.hour
        feats["Publish time (UTC)"] = pd.cut(h, [-1, 5, 11, 17, 23],
                                             labels=["Night 0–6h", "Morning 6–12h", "Afternoon 12–18h", "Evening 18–24h"]
                                             ).astype(str).replace("nan", "Unknown")
    wc = t.str.split().str.len()
    feats["Title length"] = pd.cut(wc, [0, 5, 8, 12, 100], labels=["≤5 words", "6–8 words", "9–12 words", "13+ words"]).astype(str)
    feats["Title is a question"] = np.where(t.str.contains(r"\?"), "Question", "Statement")
    feats["Number in title"] = np.where(t.str.contains(r"\d"), "Has number", "No number")
    feats["Second-person (you/your)"] = np.where(t.str.contains(r"\b(?:you|your|don.t)\b", case=False), "Speaks to viewer", "Third-person")
    feats["Series / part"] = np.where(t.str.contains(r"\bpart\b|\bep\.?\s?\d|#\d|chapter", case=False), "Series episode", "Standalone")
    theme = pd.Series("Other / unclassified", index=df.index)
    for name, pat in reversed(list(THEMES.items())):  # first match wins
        theme[t.str.contains(re.sub(r"\((?!\?)", "(?:", pat), case=False, regex=True)] = name
    feats["Title theme"] = theme

    tags = [c for c in df.columns if c.startswith("tag:")]
    for c in tags:
        feats[c[4:]] = df[c].fillna("Untagged")

    out = df.copy()
    for k, v in feats.items():
        out[f"f:{k}"] = v
    out.attrs = dict(df.attrs)
    out.attrs["dimensions"] = [c[4:] for c in tags] + [k for k in feats if k not in {c[4:] for c in tags}]
    out.attrs["custom_dims"] = [c[4:] for c in tags]
    return out


def content_points(df: pd.DataFrame, min_n: int = 2) -> pd.DataFrame:
    """For every dimension value: sample size, avg score, lift vs channel, and a confidence level."""
    base = df["traction"].mean()
    sd = df["traction"].std() or 1
    rows = []
    for dim in df.attrs["dimensions"]:
        col = f"f:{dim}"
        if df[col].nunique() < 2:
            continue
        for val, g in df.groupby(col):
            if val in ("Unknown", "nan") or len(g) < min_n:
                continue
            lift = g["traction"].mean() - base
            se = sd / np.sqrt(len(g))
            t = abs(lift) / se
            rows.append({
                "dimension": dim, "value": val, "videos": len(g),
                "avg_score": g["traction"].mean(), "lift": lift,
                "median_views": g["views"].median(),
                "hit_rate": (g["tier"].isin(["Breakout", "Strong"])).mean() * 100,
                "avg_retention": g["avg_view_pct"].mean() if "avg_view_pct" in g else np.nan,
                "avg_ctr": g["ctr"].mean() if "ctr" in g else np.nan,
                "confidence": "High" if t >= 2 and len(g) >= 4 else ("Medium" if t >= 1.2 else "Low"),
                "custom": dim in df.attrs.get("custom_dims", []),
            })
    return pd.DataFrame(rows)


def keyword_lift(df: pd.DataFrame, min_n: int = 3) -> pd.DataFrame:
    stop = set("the a an of in on to and or for is was were be with at by from that this it its his her their my our we i "
               "he she they who what why how when did do does part not no".split())
    words = df["title"].str.lower().str.findall(r"[a-z][a-z']{2,}").map(lambda ws: set(w for w in ws if w not in stop))
    base = df["traction"].mean()
    counts: dict[str, list[int]] = {}
    for i, ws in words.items():
        for w in ws:
            counts.setdefault(w, []).append(i)
    rows = [{"word": w, "videos": len(ix), "lift": df.loc[ix, "traction"].mean() - base,
             "median_views": df.loc[ix, "views"].median()}
            for w, ix in counts.items() if len(ix) >= min_n]
    return pd.DataFrame(rows).sort_values("lift", ascending=False) if rows else pd.DataFrame()


# --------------------------------------------------------------------------- diagnosis

@dataclass
class Diagnosis:
    label: str
    detail: str
    fix: str


def diagnose(row: pd.Series) -> Diagnosis:
    """Packaging (do they click?) vs payoff (do they stay / react?)."""
    pack = row.get("z_ctr", np.nan)
    if pd.isna(pack):
        pack = row.get("z_reach", 0)
    pay_parts = [row.get(k) for k in ("z_retention", "z_engage") if pd.notna(row.get(k, np.nan))]
    pay = float(np.mean(pay_parts)) if pay_parts else 0.0
    hi_p, hi_y = pack >= 0.3, pay >= 0.3
    lo_p, lo_y = pack <= -0.3, pay <= -0.3
    if hi_p and hi_y:
        return Diagnosis("Winning formula", "People click and they stay.",
                         "Reuse this premise, hook and visual treatment. Make a sequel or a sister story.")
    if hi_p and lo_y:
        return Diagnosis("Hook doesn't pay off", "The title and thumbnail pull clicks, but viewers leave or don't react.",
                         "Deliver the promise in the first 30–60s, cut slow build-up, and check the retention graph for the drop-off point.")
    if lo_p and hi_y:
        return Diagnosis("Hidden gem — packaging problem", "Viewers who find it love it, but too few click.",
                         "Re-title and re-thumbnail it: one face or object, high contrast, a curiosity gap. Test a new version.")
    if lo_p and lo_y:
        return Diagnosis("Missed on both", "Low pull and weak watch-through.",
                         "Treat it as a learning: compare its content points to your winners before making more like it.")
    if pay >= 0.3 or pack >= 0.3:
        return Diagnosis("Solid, one strength", "One side is working, the other is average.",
                         "Lift the weaker side: packaging if clicks are average, pacing if retention is average.")
    return Diagnosis("Middle of the pack", "Nothing broke, nothing stood out.",
                     "Push one variable harder next time (a bolder hook or a darker premise) to learn what moves the needle.")


def add_diagnosis(df: pd.DataFrame) -> pd.DataFrame:
    d = df.apply(diagnose, axis=1)
    out = df.copy()
    out["diagnosis"] = [x.label for x in d]
    out["diagnosis_detail"] = [x.detail for x in d]
    out["fix"] = [x.fix for x in d]
    pack = out["z_ctr"] if "z_ctr" in out else out["z_reach"]
    pay_cols = [c for c in ("z_retention", "z_engage") if c in out]
    out["packaging"] = pack.fillna(0)
    out["payoff"] = out[pay_cols].mean(axis=1).fillna(0) if pay_cols else 0.0
    out.attrs = dict(df.attrs)
    out.attrs["packaging_source"] = "Click-through rate" if "z_ctr" in df else "Age-adjusted reach"
    return out


def momentum(df: pd.DataFrame, window: int = 5) -> dict:
    d = df.sort_values("published")
    if len(d) < window * 2:
        return {"recent": d["traction"].tail(window).mean(), "prior": d["traction"].mean(), "delta": 0.0, "window": window}
    recent = d["traction"].tail(window).mean()
    prior = d["traction"].iloc[-window * 3:-window].mean()
    return {"recent": recent, "prior": prior, "delta": recent - prior, "window": window}


def cadence(df: pd.DataFrame) -> pd.DataFrame:
    d = df.sort_values("published").copy()
    d["gap_days"] = d["published"].diff().dt.total_seconds() / 86400
    d = d.dropna(subset=["gap_days"])
    if d.empty:
        return pd.DataFrame()
    d["gap"] = pd.cut(d["gap_days"], [-0.1, 2, 4, 7, 14, 10_000], labels=["≤2 days", "3–4 days", "5–7 days", "8–14 days", "15+ days"])
    return d.groupby("gap", observed=True).agg(videos=("traction", "size"), avg_score=("traction", "mean")).reset_index()


def playbook(df: pd.DataFrame, cp: pd.DataFrame) -> dict[str, list[str]]:
    """Plain-language takeaways ranked by evidence."""
    out = {"double_down": [], "rethink": [], "fix_next": [], "watch": []}
    if not cp.empty:
        trusted = cp[(cp["confidence"] != "Low") & (cp["videos"] >= 3)]
        pool = trusted if len(trusted) >= 4 else cp[cp["videos"] >= 2]
        for _, r in pool.sort_values("lift", ascending=False).head(4).iterrows():
            if r["lift"] > 2:
                out["double_down"].append(
                    f"**{r['dimension']}: {r['value']}** scores **+{r['lift']:.0f}** above your average "
                    f"across {r['videos']} videos ({r['hit_rate']:.0f}% landed Strong or Breakout).")
        for _, r in pool.sort_values("lift").head(4).iterrows():
            if r["lift"] < -2:
                out["rethink"].append(
                    f"**{r['dimension']}: {r['value']}** runs **{r['lift']:.0f}** below average across {r['videos']} videos.")
    counts = df["diagnosis"].value_counts()
    n_hook = int(counts.get("Hook doesn't pay off", 0))
    n_gem = int(counts.get("Hidden gem — packaging problem", 0))
    if n_hook >= 2:
        out["fix_next"].append(f"{n_hook} videos get the click but lose the viewer. "
                               "Tighten openings and make the first minute deliver what the thumbnail promised.")
    if n_gem >= 2:
        out["fix_next"].append(f"{n_gem} videos are hidden gems: strong watch-through, weak clicks. "
                               "Re-package them (new thumbnail/title) — the cheapest growth you have.")
    if "avg_view_pct" in df and df["avg_view_pct"].notna().any():
        long = df[df["duration_sec"] > 20 * 60]
        if len(long) >= 2 and long["avg_view_pct"].mean() < df["avg_view_pct"].median() - 5:
            out["fix_next"].append(f"Videos over 20 min hold only {long['avg_view_pct'].mean():.0f}% on average. "
                                   "Consider splitting long stories into parts.")
    m = momentum(df)
    if m["delta"] >= 4:
        out["watch"].append(f"Momentum is up: your last {m['window']} uploads average **{m['recent']:.0f}**, "
                            f"vs **{m['prior']:.0f}** before. Whatever changed recently is working.")
    elif m["delta"] <= -4:
        out["watch"].append(f"Momentum is down: last {m['window']} uploads average **{m['recent']:.0f}**, "
                            f"vs **{m['prior']:.0f}** before. Compare recent content points to older winners.")
    cad = cadence(df)
    if len(cad) >= 2 and cad["videos"].min() >= 2:
        best = cad.loc[cad["avg_score"].idxmax()]
        out["watch"].append(f"Uploads that came **{best['gap']}** after the previous one scored best (avg {best['avg_score']:.0f}).")
    if not df.attrs.get("custom_dims"):
        out["watch"].append("Add your own tag columns (e.g. *Story type*, *Visual style*, *Hook*) to the CSV — "
                            "the engine will measure each one automatically.")
    missing = [SIGNALS[k][0] for k in ("z_retention", "z_ctr", "z_convert") if k not in df.attrs.get("signals", [])]
    if missing:
        out["watch"].append(f"Scores are missing **{', '.join(missing)}**. Upload a YouTube Studio export to include them.")
    return out
