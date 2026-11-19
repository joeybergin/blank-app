"""Plotly figures, styled for a dark channel-brand dashboard.

Colors come from a validated dark-mode palette: an ordinal blue ramp for tiers,
blue/red with a gray midpoint for above/below-average lift, one blue for single series.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SURFACE = "#1a1a19"
INK = "#f0efec"
INK_2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"
BLUE = "#3987e5"
RED = "#e66767"
NEUTRAL = "#383835"
TIER_COLORS = {  # ordinal ramp: brighter = stronger (on a dark surface)
    "Breakout": "#9ec5f4", "Strong": "#5598e7", "Steady": "#256abf", "Underperforming": "#184f95",
}
TIER_ORDER = list(TIER_COLORS)
FONT = "Inter, -apple-system, Segoe UI, sans-serif"


def _base(fig: go.Figure, height: int = 380, **kw) -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK_2, size=13),
        margin=dict(l=12, r=16, t=36, b=12),
        hoverlabel=dict(bgcolor="#0d0d0d", bordercolor=AXIS, font=dict(color=INK, family=FONT)),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(color=INK_2), bgcolor="rgba(0,0,0,0)"),
        **kw,
    )
    fig.update_xaxes(automargin=True, gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(automargin=True, gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    return fig


def _short(s: str, n: int = 48) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def timeline(df: pd.DataFrame) -> go.Figure:
    d = df.sort_values("published")
    fig = go.Figure()
    for lo, hi, name in [(75, 100, "Breakout"), (60, 75, "Strong"), (40, 60, "Steady")]:
        fig.add_hline(y=lo, line=dict(color=GRID, width=1, dash="dot"))
        fig.add_annotation(x=1, xref="paper", y=lo, text=name, showarrow=False, xanchor="right", yanchor="bottom",
                           font=dict(color=MUTED, size=11))
    for tier in TIER_ORDER:
        g = d[d["tier"] == tier]
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=g["published"], y=g["traction"], mode="markers", name=tier,
            marker=dict(size=np.clip(np.sqrt(g["views"]) / 6, 9, 28), color=TIER_COLORS[tier],
                        line=dict(color=SURFACE, width=2)),
            customdata=np.stack([g["title"].map(_short), g["views"], g["reach_x"]], axis=1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{x|%b %d, %Y}<br>Traction %{y:.0f}"
                          "<br>%{customdata[1]:,.0f} views (%{customdata[2]:.1f}× expected)<extra></extra>",
        ))
    win = max(3, min(7, len(d) // 6))
    fig.add_trace(go.Scatter(
        x=d["published"], y=d["traction"].rolling(win, min_periods=2).mean(), mode="lines",
        name=f"{win}-video average", line=dict(color=INK_2, width=2, shape="spline"),
        hovertemplate="Rolling avg %{y:.0f}<extra></extra>",
    ))
    _base(fig, 420, hovermode="closest")
    fig.update_yaxes(range=[0, 102], title="Traction score")
    return fig


def tier_bars(df: pd.DataFrame) -> go.Figure:
    counts = df["tier"].value_counts().reindex(TIER_ORDER, fill_value=0)
    fig = go.Figure(go.Bar(
        y=counts.index, x=counts.values, orientation="h", marker=dict(color=[TIER_COLORS[t] for t in counts.index],
                                                                       cornerradius=4),
        text=counts.values, textposition="outside", textfont=dict(color=INK_2),
        hovertemplate="%{y}: %{x} videos<extra></extra>",
    ))
    _base(fig, 240, showlegend=False, bargap=0.35)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(visible=False)
    return fig


def lift_bars(cp: pd.DataFrame, title_col: str = "value", height: int | None = None) -> go.Figure:
    d = cp.sort_values("lift")
    colors = [BLUE if v > 1 else RED if v < -1 else NEUTRAL for v in d["lift"]]
    labels = [f"{_short(str(x), 40)}" for x in d[title_col]]
    fig = go.Figure(go.Bar(
        y=labels, x=d["lift"], orientation="h", marker=dict(color=colors, cornerradius=4),
        customdata=np.stack([d["videos"], d["avg_score"], d["median_views"], d.get("confidence", pd.Series([""] * len(d)))], axis=1),
        text=[f"{v:+.0f}  ·  n={n}" for v, n in zip(d["lift"], d["videos"])], textposition="outside",
        textfont=dict(color=INK_2, size=12), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:+.1f} vs channel average<br>Avg score %{customdata[1]:.0f} · %{customdata[0]} videos"
                      "<br>Median views %{customdata[2]:,.0f}<br>Confidence: %{customdata[3]}<extra></extra>",
    ))
    _base(fig, height or max(220, 46 * len(d) + 60), showlegend=False, bargap=0.3)
    span = max(5, d["lift"].abs().max() * 1.45)
    fig.update_xaxes(range=[-span, span], title="Traction points above / below your channel average", zeroline=True,
                     zerolinecolor=INK_2, zerolinewidth=1)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def metric_by_value(cp_dim: pd.DataFrame, col: str, label: str, fmt: str) -> go.Figure:
    d = cp_dim.dropna(subset=[col]).sort_values(col)
    fig = go.Figure(go.Bar(
        y=d["value"].map(lambda s: _short(str(s), 28)), x=d[col], orientation="h",
        marker=dict(color=BLUE, cornerradius=4), text=[fmt.format(v) for v in d[col]], textposition="outside",
        textfont=dict(color=INK_2, size=12), cliponaxis=False,
        hovertemplate="%{y}: " + fmt.replace("{:", "%{x:") + "<extra></extra>",
    ))
    _base(fig, max(200, 40 * len(d) + 70), showlegend=False, bargap=0.35, title=dict(text=label, font=dict(color=INK, size=14)))
    fig.update_xaxes(visible=False, range=[0, d[col].max() * 1.3 if len(d) else 1])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def combo_heatmap(df: pd.DataFrame, dim_a: str, dim_b: str) -> go.Figure:
    base = df["traction"].mean()
    piv = df.pivot_table(index=f"f:{dim_a}", columns=f"f:{dim_b}", values="traction", aggfunc="mean")
    n = df.pivot_table(index=f"f:{dim_a}", columns=f"f:{dim_b}", values="traction", aggfunc="size")
    lift = piv - base
    span = max(10, float(np.nanmax(np.abs(lift.values))) if lift.size else 10)
    text = [[("" if pd.isna(v) else f"{v:+.0f}<br><span style='font-size:10px'>n={int(c)}</span>")
             for v, c in zip(rv, rc)] for rv, rc in zip(lift.values, n.reindex_like(lift).fillna(0).values)]
    fig = go.Figure(go.Heatmap(
        z=lift.values, x=[_short(str(c), 22) for c in lift.columns], y=[_short(str(i), 26) for i in lift.index],
        zmin=-span, zmax=span, zmid=0,
        colorscale=[[0, "#c74545"], [0.25, RED], [0.5, NEUTRAL], [0.75, BLUE], [1, "#86b6ef"]],
        text=text, texttemplate="%{text}", textfont=dict(color=INK, size=12), xgap=2, ygap=2,
        colorbar=dict(title=dict(text="Lift", font=dict(color=MUTED)), tickfont=dict(color=MUTED), outlinewidth=0, thickness=10),
        hovertemplate=f"{dim_a}: %{{y}}<br>{dim_b}: %{{x}}<br>Lift %{{z:+.1f}}<extra></extra>",
    ))
    _base(fig, max(300, 56 * len(lift.index) + 120))
    fig.update_xaxes(side="top", gridcolor="rgba(0,0,0,0)")
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def quadrant(df: pd.DataFrame, x_label: str, highlight: str | None = None) -> go.Figure:
    fig = go.Figure()
    lim = 3.3
    for x, y, txt in [(lim, lim, "WINNING FORMULA"), (lim, -lim, "HOOK DOESN'T PAY OFF"),
                      (-lim, lim, "HIDDEN GEMS"), (-lim, -lim, "MISSED ON BOTH")]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, font=dict(color=MUTED, size=11),
                           xanchor="right" if x > 0 else "left", yanchor="top" if y > 0 else "bottom")
    d = df.copy()
    sel = d["video_id"] == highlight if highlight else pd.Series(False, index=d.index)
    for mask, color, size_scale, name in [(~sel, BLUE, 1, "Videos"), (sel, "#f0efec", 1.2, "Selected")]:
        g = d[mask]
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=g["packaging"].clip(-lim, lim), y=g["payoff"].clip(-lim, lim), mode="markers", name=name,
            marker=dict(size=np.clip(np.sqrt(g["views"]) / 6, 9, 30) * size_scale, color=color, opacity=0.85,
                        line=dict(color=SURFACE, width=2)),
            customdata=np.stack([g["title"].map(_short), g["views"], g["traction"], g["diagnosis"]], axis=1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[3]}<br>Traction %{customdata[2]:.0f} · "
                          "%{customdata[1]:,.0f} views<extra></extra>",
        ))
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.add_vline(x=0, line=dict(color=AXIS, width=1))
    _base(fig, 480, showlegend=False)
    fig.update_xaxes(range=[-lim - .2, lim + .2], title=f"Packaging → ({x_label}, vs your average)", zeroline=False)
    fig.update_yaxes(range=[-lim - .2, lim + .2], title="Payoff → (retention + engagement, vs your average)", zeroline=False)
    return fig


def signal_bars(row: pd.Series, signals: dict) -> go.Figure:
    keys = [k for k in signals if k in row and pd.notna(row[k])]
    vals = [float(row[k]) for k in keys]
    labels = [signals[k][0] for k in keys]
    fig = go.Figure(go.Bar(
        y=labels, x=vals, orientation="h", marker=dict(color=[BLUE if v > .2 else RED if v < -.2 else NEUTRAL for v in vals],
                                                       cornerradius=4),
        text=[_describe_z(v) for v in vals], textposition="outside", textfont=dict(color=INK_2, size=12), cliponaxis=False,
        hovertemplate="%{y}: %{x:+.2f} σ vs channel<extra></extra>",
    ))
    _base(fig, 60 * len(keys) + 70, showlegend=False, bargap=0.35)
    fig.update_xaxes(range=[-4.2, 4.2], title="vs your typical video", zeroline=True, zerolinecolor=INK_2)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def _describe_z(z: float) -> str:
    if z >= 1.5:
        return "far above"
    if z >= 0.5:
        return "above"
    if z > -0.5:
        return "typical"
    if z > -1.5:
        return "below"
    return "far below"


def keyword_bars(kw: pd.DataFrame, top: int = 8) -> go.Figure:
    d = pd.concat([kw.head(top), kw.tail(top)]).drop_duplicates("word")
    d = d.rename(columns={"word": "value"})
    d["avg_score"] = d["lift"]
    d["confidence"] = ""
    return lift_bars(d)


def cadence_bars(cad: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=cad["gap"].astype(str), y=cad["avg_score"], marker=dict(color=BLUE, cornerradius=4),
        text=[f"{v:.0f}<br><span style='font-size:10px'>n={n}</span>" for v, n in zip(cad["avg_score"], cad["videos"])],
        textposition="outside", textfont=dict(color=INK_2), cliponaxis=False,
        hovertemplate="Gap %{x}: avg score %{y:.0f}<extra></extra>",
    ))
    _base(fig, 300, showlegend=False, bargap=0.4)
    fig.update_yaxes(range=[0, max(100, cad["avg_score"].max() * 1.2)], title="Avg traction")
    fig.update_xaxes(title="Days since previous upload", gridcolor="rgba(0,0,0,0)")
    return fig
