import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Pub Finder", page_icon="🍺", layout="wide")

TEMPLATE = (Path(__file__).parent / "pub_map.html").read_text(encoding="utf-8")

with st.sidebar:
    st.header("🍺 Pub Finder")
    mode = st.radio("Where are you?", ["Use my current location", "Search for a place"])
    query = ""
    if mode == "Search for a place":
        query = st.text_input("Town, postcode or address", placeholder="e.g. Shoreditch, London")
    units = st.radio("Units", ["km", "miles"], horizontal=True)
    if units == "miles":
        radius_mi = st.slider("Search radius (miles)", 0.25, 3.0, 1.0, 0.25)
        radius_m = int(radius_mi * 1609.34)
    else:
        radius_km = st.slider("Search radius (km)", 0.25, 5.0, 1.5, 0.25)
        radius_m = int(radius_km * 1000)
    include_bars = st.checkbox("Include bars & beer gardens", value=False)
    st.divider()
    st.markdown(
        "**Tap a pub** on the map or in the list. It grows and three bubbles pop out:\n\n"
        "- ⚽ **Sports games** shown\n"
        "- 🍔 **Food service**\n"
        "- 🍺 **Beers on draft**\n\n"
        "Greyed-out bubbles mean that info hasn't been listed for the pub yet."
    )
    st.caption(
        "Pub data © OpenStreetMap contributors. Details come from what the "
        "community has tagged, so some pubs have more info than others."
    )

st.title("Pubs near you")

config = {
    "query": query.strip(),
    "radius": radius_m,
    "units": units,
    "includeBars": include_bars,
}
# Escape "</" so the JSON can't close the <script> tag early.
html = TEMPLATE.replace("__CONFIG__", json.dumps(config).replace("</", "<\\/"))

if mode == "Search for a place" and not query.strip():
    st.info("Type a town, postcode or address in the sidebar to search there.")
else:
    components.html(html, height=680, scrolling=False)
