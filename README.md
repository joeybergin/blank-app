# Cash Generator St Helens — customer app

A mobile-friendly Streamlit app for customers of Cash Generator St Helens
(41 Church Street, WA10 1AX), styled to match cashgenerator.co.uk (brand blue
`#0033A0`, yellow `#FFB81C`, Montserrat).

| Page | What it does |
|---|---|
| **Home** | Hero, deal of the day, this month's campaign, price drops and newest stock |
| **Shop** | Every item in the St Helens collection — search, departments, condition, price range, sort, price-drops filter, "Save" wishlist, Club price on every card, "View & buy" links to the product on cashgenerator.co.uk |
| **Spin & Win** | Animated prize wheel, one spin a day (two on Sundays), issues voucher codes that are valid for 14 days |
| **Offers** | Monthly themed campaign (changes automatically each month), weekly daily deals, always-on offers, live price drops |
| **CG Club** | Free membership sign-up with three tiers, digital membership card, welcome voucher and a savings calculator |
| **Visit & Sell** | Map, directions, how selling / buy back works, and a valuation request form |

## Stock
Stock is read live from the public feed
`https://cashgenerator.co.uk/collections/st-helens/products.json` and cached
for 10 minutes. If the feed can't be reached the app falls back to
`data/stock_snapshot.json`. Departments come from product titles (`cg/stock.py`).

## Changing promotions
Everything promotional is in **`cg/config.py`**: wheel prizes and their odds,
voucher terms, monthly campaigns, daily deals, always-on offers and membership
tiers. Also fill in `phone`, `whatsapp` and `hours` there. The site loads those
from an internal API that this app doesn't use.

## Collected data
Club sign-ups go to `data/members.csv` and valuation requests to
`data/valuations.csv` (both git-ignored). On Streamlit Community Cloud the
disk is wiped on restart, so connect a database or Google Sheet before you
rely on these files.

Vouchers are generated in the app and are not checked against the till
system, so staff should check the code format and expiry date at the counter.

## Run it
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
