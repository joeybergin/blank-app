# 🍺 Pub Finder

A Streamlit app that shows every pub near you on a map. Tap a pub and it
grows, and three bubbles pop out around it:

- ⚽ **Sports games**: sports shown, TV or big screens, sports bar
- 🍔 **Food service**: whether food is served, cuisine, kitchen hours, dietary options
- 🍺 **Beers on draft**: breweries on tap, real ale, craft beer, cider

Greyed-out bubbles mean that information hasn't been added for the pub yet.
Each pub's detail panel links to OpenStreetMap so anyone can add it.

## How it works

- **Location** comes from your browser (you'll be asked for permission), or
  you can search for a town, postcode or address in the sidebar.
- **Pubs** come from [OpenStreetMap](https://www.openstreetmap.org) through the
  Overpass API, and **search** uses Nominatim. All of it is free and needs no API key.
- The map is a Leaflet component (`pub_map.html`) embedded in `streamlit_app.py`.
- If OpenStreetMap can't be reached, the app shows clearly labelled sample pubs.

## Run it

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
