# 🩸 Traction: content analytics for story channels

A performance lab for YouTube creators who make dark, dramatic, story-driven videos. It scores every
upload against **your own channel's baseline**, breaks each video into **content points** (story type,
hook, visual style, length, title craft, timing), and shows which ones gain traction and which ones drag.

## What you get

| Tab | What it answers |
|---|---|
| **Overview** | Is the channel trending up? Which videos broke out and which fell flat? |
| **Content DNA** | Which creative choices lift the score, which hurt it, and which *combinations* work best? Which title words pull? |
| **Video diagnostics** | For any video: was the problem **packaging** (people didn't click) or **payoff** (people didn't stay)? What should you do next? |
| **Growth playbook** | Plain-language takeaways: double down, rethink, fix next, upload rhythm, and a next-video checklist. |
| **Tag & data** | Tag videos with your own labels (narrator voice, thumbnail style…), then download scored data. |

## The traction score (0–100, 50 = a typical video for your channel)

| Signal | Weight | Source |
|---|---|---|
| Reach (views vs. what a video *of that age* normally gets) | 35% | API or CSV |
| Retention (avg % viewed, compared within Shorts vs long-form) | 25% | Studio CSV |
| Engagement (likes + 2×comments + 3×shares per view) | 15% | API or CSV |
| Click-through rate | 15% | Studio CSV |
| Conversion (subs per 1k views) | 10% | Studio CSV |

Missing signals are skipped and the weights rebalance. Tiers: **Breakout** 75+, **Strong** 60–75,
**Steady** 40–60, **Underperforming** <40.

## Getting data in

1. **Demo channel**: try it straight away.
2. **YouTube channel**: enter a channel `@handle` and a free
   [YouTube Data API v3 key](https://console.cloud.google.com/apis/library/youtube.googleapis.com).
   You get public stats (views, likes, comments, duration, thumbnails). You can save the key in
   `.streamlit/secrets.toml` as `YOUTUBE_API_KEY = "..."`.
3. **Upload CSV**: YouTube Studio → Analytics → **Advanced mode** → choose *Content* → add metrics
   (Impressions, CTR, Average percentage viewed, Subscribers, Likes, Comments, Shares) → **Export → CSV**,
   then upload `Table data.csv`. You can also add the Studio CSV on top of the API pull.

**Tip:** add your own columns to the CSV, such as `Story type`, `Visual style`, `Hook` or `Narrator`.
Each one automatically becomes a content dimension. Or tag videos in-app, then download and
re-upload the file next time.

## Run it

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

You can also deploy it free on [Streamlit Community Cloud](https://streamlit.io/cloud) by pointing it
at this repo and adding `YOUTUBE_API_KEY` under the app's Secrets.

## Code layout

- `traction/engine.py`: scoring, content-point lift, diagnosis, playbook
- `traction/sources.py`: demo data, CSV normalization (YouTube Studio column names), YouTube Data API
- `traction/charts.py`: Plotly figures
- `streamlit_app.py`: the dashboard
