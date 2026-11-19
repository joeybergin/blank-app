"""Traction — a content performance lab for story-driven YouTube channels."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from traction import charts, engine, sources

st.set_page_config(page_title="Traction · Story Channel Analytics", page_icon="🩸", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1400px;}
  h1, h2, h3 {letter-spacing: -0.01em;}
  .tag {display:inline-block; padding:2px 10px; margin:2px 4px 2px 0; border-radius:999px;
        background:#2c2c2a; color:#c3c2b7; font-size:0.82rem;}
  .tag.up {background:#1c3a5e; color:#cde2fb;}
  .tag.down {background:#4a2222; color:#f3c4c4;}
  .muted {color:#898781; font-size:0.9rem;}
  .card {background:#1a1a19; border:1px solid #2c2c2a; border-radius:10px; padding:16px 18px; margin-bottom:12px;}
  .card h4 {margin:0 0 6px 0;}
</style>
""", unsafe_allow_html=True)

PLOT_CFG = {"displayModeBar": False}


def plot(fig, **kw):
    st.plotly_chart(fig, theme=None, config=PLOT_CFG, **kw)


# --------------------------------------------------------------------------- sidebar: data source

@st.cache_data(ttl=3600, show_spinner="Pulling channel data from YouTube…")
def cached_channel(channel: str, key: str, max_videos: int):
    return sources.fetch_channel(channel, key, max_videos)


with st.sidebar:
    st.title("🩸 Traction")
    st.caption("Find out what makes your stories land.")
    mode = st.radio("Data source", ["Demo channel", "YouTube channel", "Upload CSV"],
                    help="Start with the demo to see how it works.")

    raw, info = None, {}
    try:
        if mode == "Demo channel":
            raw, info = sources.demo_data()
            st.info("Showing a sample dark-storytelling channel with 64 uploads.", icon="🎭")

        elif mode == "YouTube channel":
            try:
                default_key = st.secrets["YOUTUBE_API_KEY"]
            except Exception:
                default_key = ""
            api_key = st.text_input("YouTube Data API key", value=default_key, type="password",
                                    help="Free from Google Cloud Console → APIs → YouTube Data API v3 → Credentials.")
            channel = st.text_input("Channel", placeholder="@yourhandle or channel URL")
            max_v = st.slider("Videos to analyze", 10, 500, 150, step=10)
            studio = st.file_uploader("Optional: YouTube Studio export (adds CTR, retention, subs)", type="csv")
            if api_key and channel:
                raw, info = cached_channel(channel, api_key, max_v)
                if studio is not None:
                    raw = sources.enrich(raw, sources.load_csv(studio))
            else:
                st.caption("Enter an API key and channel to begin.")

        else:
            up = st.file_uploader("YouTube Studio export or your own sheet", type="csv")
            st.caption("YouTube Studio → Analytics → **Advanced mode** → pick *Content* → Export → **Comma-separated values**. "
                       "Use the *Table data.csv* file. Extra columns like *Story type* become content dimensions.")
            if up is not None:
                raw = sources.load_csv(up)
                info = {"name": up.name.rsplit(".", 1)[0]}
    except Exception as e:  # show a friendly error, keep the app alive
        st.error(str(e))
        raw = None

    if raw is not None:
        st.divider()
        min_age = st.slider("Ignore videos younger than (days)", 0, 14, 2,
                            help="Brand-new uploads haven't had time to find their audience.")
        formats = st.segmented_control("Formats", ["Long-form", "Shorts"], selection_mode="multi",
                                       default=["Long-form", "Shorts"])

if raw is None:
    st.title("Traction")
    st.markdown("#### Pick a data source in the sidebar to analyze a channel.")
    st.markdown(
        "- **Demo channel**: explore with sample data.\n"
        "- **YouTube channel**: live public stats via the YouTube Data API.\n"
        "- **Upload CSV**: a YouTube Studio export, which adds CTR, retention and subscriber data.")
    st.stop()

# --------------------------------------------------------------------------- apply in-app tags, filter, score

src_key = f"{mode}:{info.get('name', '')}"
if st.session_state.get("src_key") != src_key:
    st.session_state.src_key = src_key
    st.session_state.tags = pd.DataFrame({"video_id": raw["video_id"]}).set_index("video_id")
    for c in [c for c in raw.columns if c.startswith("tag:")]:
        st.session_state.tags[c[4:]] = raw.set_index("video_id")[c]

tags: pd.DataFrame = st.session_state.tags
data = raw.drop(columns=[c for c in raw.columns if c.startswith("tag:")]).copy()
for c in tags.columns:
    data[f"tag:{c}"] = data["video_id"].map(tags[c]).where(lambda s: s.notna() & (s.astype(str).str.strip() != ""))
data = data.drop(columns=[c for c in data.columns if c.startswith("tag:") and data[c].isna().all()])

now = pd.Timestamp.now(tz="UTC")
if data["published"].notna().any():
    data = data[(data["published"].isna()) | ((now - data["published"]).dt.days >= min_age)]
is_short = data["duration_sec"].fillna(600) <= 60
fmt_sel = formats or ["Long-form", "Shorts"]
data = data[(is_short & ("Shorts" in fmt_sel)) | (~is_short & ("Long-form" in fmt_sel))]

if len(data) < 5:
    st.warning("Need at least 5 videos to find patterns. Loosen the filters or add more videos.")
    st.stop()

df = engine.add_diagnosis(engine.score(data, now))
cp = engine.content_points(df)
signals_used = df.attrs["signals"]
mom = engine.momentum(df)

# --------------------------------------------------------------------------- header + KPIs

st.title(info.get("name", "Your channel"))
subs = f"{info['subscribers']:,} subscribers · " if info.get("subscribers") else ""
st.markdown(f"<span class='muted'>{subs}{len(df)} videos analyzed · signals used: "
            f"{', '.join(engine.SIGNALS[s][0] for s in signals_used)}</span>", unsafe_allow_html=True)

d_sorted = df.sort_values("published")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Avg traction score", f"{df['traction'].mean():.0f}", border=True,
          help="0–100. 50 = a typical video for this channel. Built from reach (age-adjusted), retention, engagement, CTR and conversion.",
          chart_data=d_sorted["traction"].rolling(5, min_periods=1).mean().round(1).tolist(), chart_type="area")
k2.metric(f"Last {mom['window']} uploads", f"{mom['recent']:.0f}", f"{mom['delta']:+.0f} vs before", border=True)
k3.metric("Hit rate", f"{df['tier'].isin(['Breakout', 'Strong']).mean() * 100:.0f}%", border=True,
          help="Share of videos that scored Strong (60+) or Breakout (75+).")
k4.metric("Median views", f"{df['views'].median():,.0f}", border=True,
          chart_data=d_sorted["views"].tolist(), chart_type="bar")
if "avg_view_pct" in df and df["avg_view_pct"].notna().any():
    k5.metric("Avg % viewed", f"{df['avg_view_pct'].mean():.0f}%", border=True)
else:
    k5.metric("Engagement rate", f"{df['engagement_rate'].median():.1f}%", border=True,
              help="(likes + 2×comments + 3×shares) per 100 views, median.")

tab_over, tab_dna, tab_diag, tab_play, tab_data = st.tabs(
    ["📈 Overview", "🧬 Content DNA", "🔍 Video diagnostics", "🗺️ Growth playbook", "🏷️ Tag & data"])

# --------------------------------------------------------------------------- overview

with tab_over:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Traction over time")
        st.caption("Each dot is a video (bigger = more views). The line is the rolling average: your trajectory.")
        plot(charts.timeline(df))
    with c2:
        st.subheader("Tier mix")
        plot(charts.tier_bars(df))
        st.markdown(
            "<span class='muted'>**Breakout** 75+ · **Strong** 60–75 · **Steady** 40–60 · **Underperforming** below 40. "
            "Scored against <i>your own</i> channel, so it stays meaningful as you grow.</span>", unsafe_allow_html=True)

    def video_cards(rows: pd.DataFrame):
        for _, r in rows.iterrows():
            with st.container(border=True):
                a, b = st.columns([1, 3]) if pd.notna(r.get("thumbnail")) else (None, st.container())
                if a is not None:
                    a.image(r["thumbnail"], width="stretch")
                b.markdown(f"**{r['title']}**")
                b.markdown(f"<span class='muted'>Traction **{r['traction']:.0f}** · {r['views']:,.0f} views "
                           f"({r['reach_x']:.1f}× expected) · {r['diagnosis']}</span>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔥 Top performers")
        video_cards(df.nlargest(5, "traction"))
    with c2:
        st.subheader("🧊 Needs work")
        video_cards(df.nsmallest(5, "traction"))

# --------------------------------------------------------------------------- content DNA

with tab_dna:
    st.subheader("Which content points gain traction?")
    st.caption("How much each choice lifts or drags the traction score versus the channel average. "
               "Blue = above average, red = below. *n* = number of videos. Small *n* means treat it as a hunch, not a rule.")
    if cp.empty:
        st.info("Not enough variety yet. Tag your videos in **Tag & data** to unlock this view.")
    else:
        dims = [d for d in df.attrs["dimensions"] if d in set(cp["dimension"])]
        dim = st.pills("Content dimension", dims, default=dims[0], key="dna_dim") or dims[0]
        sub = cp[cp["dimension"] == dim]
        c1, c2 = st.columns([3, 2])
        with c1:
            plot(charts.lift_bars(sub))
        with c2:
            if sub["avg_retention"].notna().any():
                plot(charts.metric_by_value(sub, "avg_retention", "Avg % viewed", "{:.0f}%"))
            if sub["avg_ctr"].notna().any():
                plot(charts.metric_by_value(sub, "avg_ctr", "Avg click-through rate", "{:.1f}%"))
            if not (sub["avg_retention"].notna().any() or sub["avg_ctr"].notna().any()):
                plot(charts.metric_by_value(sub, "median_views", "Median views", "{:,.0f}"))

        st.divider()
        st.subheader("Strongest signals across everything")
        trusted = cp[cp["videos"] >= 3]
        movers = pd.concat([trusted.nlargest(8, "lift"), trusted.nsmallest(8, "lift")]).drop_duplicates()
        movers = movers.assign(label=movers["dimension"] + ": " + movers["value"].astype(str))
        plot(charts.lift_bars(movers, title_col="label"))

        st.divider()
        st.subheader("Winning combinations")
        st.caption("Pair two dimensions to find combos that beat either alone (e.g. a story type with a particular hook).")
        a, b = st.columns(2)
        dim_a = a.selectbox("Rows", dims, index=0)
        dim_b = b.selectbox("Columns", [d for d in dims if d != dim_a], index=0)
        plot(charts.combo_heatmap(df, dim_a, dim_b))

        kw = engine.keyword_lift(df)
        if not kw.empty and len(kw) >= 4:
            st.divider()
            st.subheader("Title words")
            st.caption("Words that appear in 3+ titles, ranked by the average score of videos using them.")
            plot(charts.keyword_bars(kw))

# --------------------------------------------------------------------------- diagnostics

with tab_diag:
    st.subheader("Packaging vs payoff")
    st.caption(f"Right = more people clicked than usual ({df.attrs['packaging_source'].lower()}). "
               "Up = viewers stayed and reacted more than usual. Each corner needs a different fix.")
    options = df.sort_values("published", ascending=False)
    labels = {r.video_id: f"{r.title}  ·  {r.published:%b %d, %Y}" if pd.notna(r.published) else r.title
              for r in options.itertuples()}
    pick = st.selectbox("Inspect a video", list(labels), format_func=labels.get)
    c1, c2 = st.columns([3, 2])
    with c1:
        plot(charts.quadrant(df, df.attrs["packaging_source"], pick))
        counts = df["diagnosis"].value_counts()
        st.markdown(" ".join(f"<span class='tag'>{k}: {v}</span>" for k, v in counts.items()), unsafe_allow_html=True)
    with c2:
        r = df.set_index("video_id").loc[pick]
        if pd.notna(r.get("thumbnail")):
            st.image(r["thumbnail"], width="stretch")
        st.markdown(f"#### {r['title']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Traction", f"{r['traction']:.0f}", r["tier"], delta_color="off")
        m2.metric("Views", f"{r['views']:,.0f}", f"{r['reach_x']:.1f}× expected", delta_color="off")
        if pd.notna(r.get("avg_view_pct")):
            m3.metric("% viewed", f"{r['avg_view_pct']:.0f}%")
        elif pd.notna(r.get("engagement_rate")):
            m3.metric("Engagement", f"{r['engagement_rate']:.1f}%")
        st.markdown(f"<div class='card'><h4>{r['diagnosis']}</h4>{r['diagnosis_detail']}<br><br>"
                    f"<b>Next move:</b> {r['fix']}</div>", unsafe_allow_html=True)
        plot(charts.signal_bars(r, engine.SIGNALS))
        lift_map = cp.set_index(["dimension", "value"])["lift"] if not cp.empty else pd.Series(dtype=float)
        chips = []
        for dim in df.attrs["dimensions"]:
            val = r[f"f:{dim}"]
            l = lift_map.get((dim, val), 0.0)
            cls = "up" if l > 2 else "down" if l < -2 else ""
            chips.append(f"<span class='tag {cls}' title='{l:+.0f} lift'>{dim}: {val}</span>")
        st.markdown("**Content points in this video**<br>" + "".join(chips), unsafe_allow_html=True)
        st.caption("Blue chips usually help on this channel; red chips usually hurt.")

# --------------------------------------------------------------------------- playbook

with tab_play:
    pb = engine.playbook(df, cp)
    sections = [
        ("🔥 Double down", "double_down", "These content points consistently beat your average. Make more of them."),
        ("🧯 Rethink", "rethink", "These consistently drag. Change them or drop them."),
        ("🛠️ Fix next", "fix_next", "Specific craft problems the data points to."),
        ("👁️ Watch", "watch", "Trends and housekeeping."),
    ]
    c1, c2 = st.columns(2)
    for i, (title, key, blurb) in enumerate(sections):
        with (c1 if i % 2 == 0 else c2):
            with st.container(border=True):
                st.subheader(title)
                st.caption(blurb)
                items = pb[key]
                if items:
                    for it in items:
                        st.markdown(f"- {it}")
                else:
                    st.markdown("<span class='muted'>Nothing stands out here yet.</span>", unsafe_allow_html=True)

    cad = engine.cadence(df)
    if len(cad) >= 2:
        st.subheader("Upload rhythm")
        st.caption("Average score by how long it had been since the previous upload.")
        plot(charts.cadence_bars(cad))

    st.subheader("Next-video checklist")
    best = cp[(cp["videos"] >= 3)].sort_values("lift", ascending=False).groupby("dimension").head(1) if not cp.empty else cp
    best = best[best["lift"] > 0] if not best.empty else best
    if not best.empty:
        st.caption("The best-performing choice in each dimension. A starting recipe to test, not a cage.")
        for _, b in best.sort_values("lift", ascending=False).iterrows():
            st.checkbox(f"**{b['dimension']}** → {b['value']}  (+{b['lift']:.0f})", key=f"chk_{b['dimension']}")

# --------------------------------------------------------------------------- tag & data

with tab_data:
    st.subheader("Tag your videos")
    st.caption("Label each video with the creative choices you made: story type, visual style, hook, narrator voice, "
               "music, thumbnail style, anything. Every column becomes a dimension in **Content DNA**. "
               "Download the result and re-upload it next time so you don't have to re-tag.")
    new_col = st.text_input("Add a tag column", placeholder="e.g. Thumbnail style")
    if st.button("Add column") and new_col.strip() and new_col.strip() not in tags.columns:
        st.session_state.tags[new_col.strip()] = None
        st.rerun()

    editor_src = raw[["video_id", "title"]].set_index("video_id").join(tags)
    edited = st.data_editor(
        editor_src.reset_index(), hide_index=True, disabled=["video_id", "title"], height=420,
        column_config={"video_id": None, "title": st.column_config.TextColumn("Video", width="large")},
        key=f"tag_editor_{src_key}_{len(tags.columns)}",
    )
    if st.button("Apply tags", type="primary"):
        st.session_state.tags = edited.set_index("video_id").drop(columns="title")
        st.rerun()

    st.divider()
    st.subheader("Scored data")
    cols = ["title", "published", "views", "traction", "tier", "diagnosis", "reach_x", "engagement_rate"] + \
           [c for c in ("ctr", "avg_view_pct", "subs_gained") if c in df]
    st.dataframe(df[cols].sort_values("traction", ascending=False), hide_index=True, column_config={
        "traction": st.column_config.ProgressColumn("Traction", min_value=0, max_value=100, format="%.0f"),
        "reach_x": st.column_config.NumberColumn("Reach vs expected", format="%.1f×"),
        "engagement_rate": st.column_config.NumberColumn("Engagement %", format="%.1f"),
        "published": st.column_config.DatetimeColumn("Published", format="MMM D, YYYY"),
        "views": st.column_config.NumberColumn("Views", format="localized"),
    })
    export = raw.drop(columns=[c for c in raw.columns if c.startswith("tag:")]).merge(
        st.session_state.tags.reset_index(), on="video_id", how="left")
    a, b = st.columns(2)
    a.download_button("⬇️ Download tagged data (re-upload later)", export.to_csv(index=False), "traction_tagged.csv", "text/csv")
    b.download_button("⬇️ Download scores", df[cols + ["video_id", "fix"]].to_csv(index=False), "traction_scores.csv", "text/csv")

    with st.expander("How the traction score works"):
        st.markdown("""
Every video is compared to **this channel's own typical video**, so scores stay meaningful whether you have 500 subscribers or 500k.

| Signal | Weight | What it measures |
|---|---|---|
""" + "\n".join(f"| {v[0]} | {int(v[1] * 100)}% | {v[2]} |" for v in engine.SIGNALS.values()) + """

- **Reach is age-adjusted.** Most views arrive in a video's first couple of weeks, so a 3-day-old upload is compared to what
  3-day-old uploads normally get, not to videos that have had months.
- **Retention is compared within format**, since Shorts naturally hold a higher percentage.
- Each signal becomes a robust z-score (median-based, so one viral hit doesn't skew everything), combined by weight,
  then mapped so **50 = typical**, **60+ = Strong**, **75+ = Breakout**.
- Signals that aren't available are skipped and the weights re-balance. Upload a YouTube Studio export to include CTR, retention and subscribers.
- **Content-point lift** = average score of videos with that trait minus the channel average. Confidence rises with sample size and effect size.
""")
