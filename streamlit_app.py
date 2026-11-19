"""Cash Generator St Helens — customer app.

Run with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import csv
import datetime as dt
import random
import re
import secrets
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from cg import config as C
from cg.stock import CATEGORY_ICONS, Product, load_stock
from cg.ui import CSS, esc, gbp, hero, tile, wheel_html

st.set_page_config(page_title="Cash Generator St Helens", page_icon="💷", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

DATA = Path(__file__).parent / "data"
MEMBERS_CSV = DATA / "members.csv"
BASE_TIER = C.MEMBERSHIP_TIERS[0]

ss = st.session_state
ss.setdefault("saved", [])  # product ids
ss.setdefault("vouchers", [])  # dicts
ss.setdefault("last_spin", None)  # date
ss.setdefault("spins_today", 0)
ss.setdefault("spin_id", 0)
ss.setdefault("member", None)


@st.cache_data(ttl=600, show_spinner="Checking what's in store…")
def stock() -> tuple[list[Product], str]:
    return load_stock()


PRODUCTS, SOURCE = stock()
BY_ID = {p.id: p for p in PRODUCTS}
TODAY = dt.date.today()


# --------------------------------------------------------------------------
# Shared bits
# --------------------------------------------------------------------------
def member_pct() -> int:
    return ss.member["discount"] if ss.member else BASE_TIER["discount"]


def product_card(p: Product, key: str) -> None:
    with st.container(border=True):
        if p.image:
            st.markdown(f'<img class="cg-img" src="{esc(p.image)}" alt="{esc(p.title)}" loading="lazy">',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="cg-noimg">{CATEGORY_ICONS.get(p.category, "🛍️")}</div>',
                        unsafe_allow_html=True)
        badges = []
        if p.saving:
            badges.append(f'<span class="cg-badge sale">SAVE {p.saving_pct}%</span>')
        badges.append(f'<span class="cg-badge {"new" if p.condition.startswith("New") else ""}">'
                      f'{esc(p.condition)}</span>')
        was = f'<span class="cg-was">{gbp(p.was)}</span>' if p.saving else ""
        label = "Your Club price" if ss.member else "Club price"
        st.markdown(
            f'{"".join(badges)}<div class="cg-card-title" title="{esc(p.title)}">{esc(p.title)}</div>'
            f'<div><span class="cg-price">{gbp(p.price)}</span>{was}</div>'
            f'<div class="cg-member">⭐ {label}: {gbp(p.member_price(member_pct()))} in store</div>',
            unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        c1.link_button("View & buy", p.url, type="primary", use_container_width=True)
        saved = p.id in ss.saved
        if c2.button("♥ Saved" if saved else "♡ Save", key=f"save-{key}-{p.id}", use_container_width=True):
            ss.saved.remove(p.id) if saved else ss.saved.append(p.id)
            st.rerun()


def product_grid(items: list[Product], key: str, cols: int = 4) -> None:
    for i in range(0, len(items), cols):
        row = st.columns(cols)
        for col, p in zip(row, items[i:i + cols]):
            with col:
                product_card(p, key)


def daily_deal() -> tuple[str, str]:
    return C.DAILY_DEALS[TODAY.weekday()]


def footer() -> None:
    contact = []
    if C.STORE["phone"]:
        contact.append(f'📞 <a href="tel:{C.STORE["phone"].replace(" ", "")}">{C.STORE["phone"]}</a>')
    contact.append(f'✉️ <a href="mailto:{C.STORE["email"]}">{C.STORE["email"]}</a>')
    feed = "Live stock" if SOURCE == "live" else f"Stock as of {SOURCE.split()[-1]}"
    st.markdown(
        f'<div class="cg-footer"><b>{C.STORE["name"]}</b> · {C.STORE["address"]}<br>'
        f'{" · ".join(contact)} · <a href="{C.STORE["store_page"]}" target="_blank">Store page</a><br>'
        f'<span style="opacity:.75">{feed} · {len(PRODUCTS)} items · Prices and availability can change '
        f'quickly — items sell fast!</span></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def page_home() -> None:
    st.markdown(hero(f'Cash Generator <span class="accent">St Helens</span>',
                     "Buy, sell & buy back — great prices on quality pre-owned tech, right on Church Street."),
                unsafe_allow_html=True)
    name, deal = daily_deal()
    month = C.MONTHLY_OFFERS[TODAY.month]
    st.markdown(f'<div class="cg-strip">🔥 {name}: {deal} &nbsp;|&nbsp; 📅 {month["theme"]} is on now</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(tile("🎡", "Spin & Win", "Spin the prize wheel every day for vouchers up to £50 off."),
                    unsafe_allow_html=True)
        st.page_link(PAGES["spin"], label="Spin now →")
    with c2:
        st.markdown(tile("⭐", "Join CG Club — free",
                         f"Instant {BASE_TIER['discount']}% off pre-owned, trade-in bonuses and early access."),
                    unsafe_allow_html=True)
        st.page_link(PAGES["club"], label="Join the club →")
    with c3:
        st.markdown(tile("💷", "Sell to us", "Phones, laptops, consoles, gold — paid on the spot."),
                    unsafe_allow_html=True)
        st.page_link(PAGES["visit"], label="How selling works →")

    drops = sorted([p for p in PRODUCTS if p.saving], key=lambda p: -p.saving_pct)
    if drops:
        st.subheader("💥 Price drops")
        product_grid(drops[:8], "home-drops")

    st.subheader("🆕 Just in")
    newest = sorted(PRODUCTS, key=lambda p: p.published, reverse=True)
    product_grid([p for p in newest if p not in drops[:8]][:8], "home-new")
    st.page_link(PAGES["shop"], label=f"Browse all {len(PRODUCTS)} items in store →", icon="🛍️")


def page_shop() -> None:
    st.title("Shop St Helens stock")
    st.caption(f"{len(PRODUCTS)} items available for delivery or collection from {C.STORE['address']}.")

    cats = sorted({p.category for p in PRODUCTS}, key=lambda c: (c == "Other", c))
    counts = {c: sum(p.category == c for p in PRODUCTS) for c in cats}
    cat = st.pills("Department", ["All"] + cats, default="All",
                   format_func=lambda c: "All" if c == "All" else f"{CATEGORY_ICONS.get(c, '')} {c} ({counts[c]})")

    f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
    q = f1.text_input("Search", placeholder="e.g. iPhone 15, Xbox, Canon…", label_visibility="collapsed")
    conds = sorted({p.condition for p in PRODUCTS})
    cond = f2.multiselect("Condition", conds, placeholder="Any condition", label_visibility="collapsed")
    sort = f3.selectbox("Sort", ["Newest", "Price: low to high", "Price: high to low", "Biggest saving"],
                        label_visibility="collapsed")
    deals_only = f4.toggle("Price drops only")
    hi = max((p.price for p in PRODUCTS), default=100)
    lo_p, hi_p = st.slider("Price range (£)", 0, int(hi) + 1, (0, int(hi) + 1))

    items = PRODUCTS
    if cat and cat != "All":
        items = [p for p in items if p.category == cat]
    if q:
        words = [w for w in re.split(r"\s+", q.lower()) if w]
        items = [p for p in items if all(w in p.title.lower() for w in words)]
    if cond:
        items = [p for p in items if p.condition in cond]
    if deals_only:
        items = [p for p in items if p.saving]
    items = [p for p in items if lo_p <= p.price <= hi_p]
    keyf = {"Newest": (lambda p: p.published, True), "Price: low to high": (lambda p: p.price, False),
            "Price: high to low": (lambda p: p.price, True), "Biggest saving": (lambda p: p.saving, True)}[sort]
    items = sorted(items, key=keyf[0], reverse=keyf[1])

    st.markdown(f"**{len(items)}** item{'s' if len(items) != 1 else ''} found")
    if not items:
        st.info("Nothing matches right now — new stock arrives every day. "
                "Join CG Club and we'll let you know about new arrivals.")
    product_grid(items, "shop")

    if ss.saved:
        st.divider()
        st.subheader(f"♥ Your saved items ({len(ss.saved)})")
        saved = [BY_ID[i] for i in ss.saved if i in BY_ID]
        total = sum(p.price for p in saved)
        st.caption(f"Total {gbp(total)} · with your Club discount {gbp(total * (1 - member_pct() / 100))}")
        product_grid(saved, "saved")


def _spin_allowance() -> int:
    double = TODAY.weekday() == 6 or (TODAY.month == 10 and TODAY.day == 31)
    return 2 if double else 1


def _do_spin() -> None:
    """Button callback: runs before the page re-renders so counters are already up to date."""
    if ss.last_spin != TODAY:
        ss.spins_today = 0
    if ss.spins_today >= _spin_allowance():
        return
    weights = [p["weight"] for p in C.WHEEL_PRIZES]
    target = random.choices(range(len(C.WHEEL_PRIZES)), weights=weights)[0]
    prize = C.WHEEL_PRIZES[target]
    ss.spin_id += 1
    ss.spins_today += 1
    ss.last_spin = TODAY
    if prize["code_prefix"]:
        code = f"{prize['code_prefix']}-STH-{secrets.token_hex(2).upper()}"
        expires = TODAY + dt.timedelta(days=C.VOUCHER_VALID_DAYS)
        ss.vouchers.insert(0, {"label": prize["label"], "detail": prize["detail"], "code": code,
                               "expires": expires.isoformat()})
        html_ = (f'<div style="font-weight:800;font-size:22px;color:{C.BLUE}">🎉 You won '
                 f'{esc(prize["label"])}!</div><div>{esc(prize["detail"])}</div>'
                 f'<div style="font-weight:800;letter-spacing:2px;margin-top:6px">{code}</div>')
    else:
        html_ = f'<div style="font-weight:800;font-size:20px;color:{C.BLUE}">{esc(prize["detail"])}</div>'
    ss.spin_result = (target, html_)
    ss.pending_spin = True


def page_spin() -> None:
    st.title("🎡 Spin & Win")
    st.caption("Spin the wheel for a voucher to use in store at St Helens. New spins every day!")

    if ss.last_spin != TODAY:
        ss.spins_today = 0
    left = _spin_allowance() - ss.spins_today
    labels = [p["label"] for p in C.WHEEL_PRIZES]

    c1, c2 = st.columns([3, 2])
    with c2:
        st.markdown(tile("🎁", "How it works",
                         f"Tap SPIN for a chance to win discounts and trade-in boosts. Vouchers are valid for "
                         f"{C.VOUCHER_VALID_DAYS} days. Sundays = double spins!"), unsafe_allow_html=True)
        st.write("")
        st.metric("Spins left today", max(left, 0))
        st.button("SPIN THE WHEEL", type="primary", disabled=left <= 0, use_container_width=True,
                  on_click=_do_spin)
        if left <= 0:
            st.info("You've used today's spins — come back tomorrow for another go!")

    target, result_html = None, ""
    if ss.pop("pending_spin", None) is not None:
        target, result_html = ss.spin_result
    with c1:
        components.html(wheel_html(labels, target, ss.spin_id, result_html), height=470)

    if ss.vouchers:
        st.subheader("🎟️ My vouchers")
        vc = st.columns(min(len(ss.vouchers), 3))
        for i, v in enumerate(ss.vouchers):
            with vc[i % len(vc)]:
                st.markdown(f'<div class="cg-voucher"><b>{esc(v["label"])}</b><div>{esc(v["detail"])}</div>'
                            f'<div class="code">{v["code"]}</div><small>Valid until '
                            f'{dt.date.fromisoformat(v["expires"]).strftime("%d %b %Y")}</small></div>',
                            unsafe_allow_html=True)
        st.caption("📸 Screenshot your voucher and show it at the till. " + C.VOUCHER_TERMS)


def page_offers() -> None:
    month = C.MONTHLY_OFFERS[TODAY.month]
    st.markdown(hero(f'{TODAY.strftime("%B")}: <span class="accent">{esc(month["theme"])}</span>',
                     "This month's offers at Cash Generator St Helens.", logo=False), unsafe_allow_html=True)
    st.write("")
    cols = st.columns(len(month["offers"]))
    for col, o in zip(cols, month["offers"]):
        col.markdown(tile("🏷️", o, ""), unsafe_allow_html=True)

    name, deal = daily_deal()
    st.subheader("📆 Deal of the day")
    st.markdown(f'<div class="cg-strip" style="font-size:1.1rem">{name}: {deal}</div>', unsafe_allow_html=True)
    with st.expander("See this week's daily deals"):
        for d in range(7):
            n, txt = C.DAILY_DEALS[d]
            mark = " ← today" if d == TODAY.weekday() else ""
            st.markdown(f"**{dt.date(2024, 1, 1 + d).strftime('%A')} — {n}:** {txt}{mark}")

    st.subheader("💡 Always on")
    ev = C.EVERGREEN_OFFERS
    for i in range(0, len(ev), 3):
        row = st.columns(3)
        for col, o in zip(row, ev[i:i + 3]):
            col.markdown(tile(o["icon"], o["title"], o["text"]), unsafe_allow_html=True)
            col.write("")

    drops = sorted([p for p in PRODUCTS if p.saving], key=lambda p: -p.saving)
    if drops:
        st.subheader(f"💥 Price drops in store now ({len(drops)})")
        st.caption(f"Together these save you {gbp(sum(p.saving for p in drops))}.")
        product_grid(drops, "offers")
    st.caption("Offers available in store at St Helens while stocks last. Ask a team member for details.")


def tier_for(spend: float) -> dict:
    return [t for t in C.MEMBERSHIP_TIERS if spend >= t["spend"]][-1]


def save_member(row: dict) -> None:
    DATA.mkdir(exist_ok=True)
    new = not MEMBERS_CSV.exists()
    with MEMBERS_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def page_club() -> None:
    st.title("⭐ CG Club membership")
    st.caption("Free to join. Save every time you shop, earn points and get more for your trade-ins.")

    cols = st.columns(len(C.MEMBERSHIP_TIERS))
    for col, t in zip(cols, C.MEMBERSHIP_TIERS):
        req = "Free on sign-up" if not t["spend"] else f"Spend £{t['spend']} in 12 months"
        perks = "".join(f"<li>{esc(p)}</li>" for p in t["perks"])
        col.markdown(f'<div class="cg-tile" style="border-top-color:{t["colour"]}">'
                     f'<h4>{t["name"]}</h4><p><b>{t["discount"]}% off</b> · {req}</p>'
                     f'<ul style="padding-left:18px;margin:.5rem 0 0;font-size:.88rem">{perks}</ul></div>',
                     unsafe_allow_html=True)
    st.write("")

    if ss.member:
        m = ss.member
        st.subheader("Your membership card")
        st.markdown(f'<div class="cg-member-card"><div style="display:flex;justify-content:space-between">'
                    f'<b>CASH GENERATOR</b><span class="tier">{m["tier"].upper()}</span></div>'
                    f'<div class="num">{m["number"]}</div><div>{esc(m["name"])}</div>'
                    f'<small style="opacity:.8">Member since {m["joined"]} · St Helens</small></div>',
                    unsafe_allow_html=True)
        st.caption("Show this card at the till to get your discount. Screenshot it to keep it handy.")
        if st.button("Sign out"):
            ss.member = None
            st.rerun()
    else:
        st.subheader("Join free in 30 seconds")
        with st.form("join"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name*")
            email = c2.text_input("Email*")
            phone = c1.text_input("Mobile")
            bday = c2.date_input("Birthday (for your birthday treat)", value=None,
                                 min_value=dt.date(1920, 1, 1), max_value=TODAY, format="DD/MM/YYYY")
            interests = st.multiselect("What are you into?", sorted({p.category for p in PRODUCTS}))
            consent = st.checkbox("Send me members-only offers and new-stock alerts by email/SMS")
            ok = st.form_submit_button("Join CG Club", type="primary")
        if ok:
            if not name.strip() or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
                st.error("Please enter your name and a valid email address.")
            else:
                number = f"CG {secrets.randbelow(10**4):04d} {secrets.randbelow(10**4):04d} STH"
                ss.member = {"name": name.strip(), "email": email.strip(), "number": number,
                             "tier": BASE_TIER["name"], "discount": BASE_TIER["discount"],
                             "joined": TODAY.strftime("%b %Y")}
                save_member({"joined": TODAY.isoformat(), "number": number, "name": name.strip(),
                             "email": email.strip(), "phone": phone.strip(),
                             "birthday": bday.isoformat() if bday else "", "interests": "; ".join(interests),
                             "marketing_consent": consent})
                code = f"WELCOME-STH-{secrets.token_hex(2).upper()}"
                ss.vouchers.insert(0, {"label": "WELCOME £5", "detail": "£5 off your first purchase over £30",
                                       "code": code,
                                       "expires": (TODAY + dt.timedelta(days=30)).isoformat()})
                st.balloons()
                st.rerun()

    st.subheader("🧮 What could you save?")
    c1, c2 = st.columns(2)
    spend = c1.slider("Your typical spend per year (£)", 0, 2000, 400, step=50)
    trade = c2.slider("Value of items you trade in per year (£)", 0, 1000, 150, step=25)
    t = tier_for(spend)
    saving = spend * t["discount"] / 100
    bonus = trade * t["trade_bonus"] / 100
    points = spend * C.POINTS_PER_POUND
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Your tier", t["name"])
    m2.metric("Shopping savings", gbp(saving))
    m3.metric("Extra trade-in credit", gbp(bonus))
    m4.metric("Points earned", f"{points:,.0f}", f"worth {gbp(points * C.POINTS_VALUE)}")
    st.success(f"That's around **{gbp(saving + bonus + points * C.POINTS_VALUE)} a year** back in your pocket.")


def page_visit() -> None:
    st.title("📍 Visit & sell")
    c1, c2 = st.columns([3, 2])
    with c1:
        q = C.STORE["address"].replace(" ", "+")
        components.iframe(f"https://maps.google.com/maps?q={q}&z=16&output=embed", height=340)
    with c2:
        st.markdown(f"### {C.STORE['name']}\n{C.STORE['address']}")
        if C.STORE["hours"]:
            st.markdown("**Opening hours**\n\n" + "\n".join(f"- {d}: {h}" for d, h in C.STORE["hours"].items()))
        else:
            st.markdown(f"**Opening hours:** see the [store page]({C.STORE['store_page']}) for today's times.")
        b1, b2 = st.columns(2)
        b1.link_button("🧭 Directions", f"https://www.google.com/maps/dir/?api=1&destination={q}",
                       type="primary", use_container_width=True)
        if C.STORE["phone"]:
            b2.link_button("📞 Call", f"tel:{C.STORE['phone'].replace(' ', '')}", use_container_width=True)
        else:
            b2.link_button("✉️ Email", f"mailto:{C.STORE['email']}", use_container_width=True)
        if C.STORE["whatsapp"]:
            st.link_button("💬 WhatsApp us", f"https://wa.me/44{C.STORE['whatsapp']}", use_container_width=True)

    st.subheader("How to get cash")
    s1, s2, s3 = st.columns(3)
    s1.markdown(tile("1️⃣", "Bring it in", "Phones, laptops, consoles, tablets, cameras, gold & more. "
                     "Bring photo ID and any chargers or boxes."), unsafe_allow_html=True)
    s2.markdown(tile("2️⃣", "Get a valuation", "Our friendly team tests your item and gives you a price — "
                     "no obligation."), unsafe_allow_html=True)
    s3.markdown(tile("3️⃣", "Get paid", "Take cash on the spot, or choose store credit for a trade-in bonus. "
                     "Or use buy back and reclaim it later."), unsafe_allow_html=True)

    st.subheader("Get a rough idea first")
    st.caption("Tell us what you've got and we'll have it ready to look at when you arrive.")
    with st.form("quote"):
        c1, c2 = st.columns(2)
        item = c1.text_input("What are you selling?", placeholder="e.g. iPhone 13 128GB")
        cond = c2.selectbox("Condition", ["Like new", "Good", "Fair", "Faulty"])
        extras = st.multiselect("Comes with", ["Box", "Charger", "Receipt", "Controllers/accessories"])
        contact = st.text_input("Email or mobile so we can get back to you")
        sent = st.form_submit_button("Request a valuation", type="primary")
    if sent:
        if not item or not contact:
            st.error("Please tell us the item and how to reach you.")
        else:
            DATA.mkdir(exist_ok=True)
            path = DATA / "valuations.csv"
            new = not path.exists()
            with path.open("a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["date", "item", "condition", "extras", "contact"])
                w.writerow([dt.datetime.now().isoformat(timespec="minutes"), item, cond, "; ".join(extras), contact])
            st.success("Thanks! The St Helens team will be in touch, usually within a day.")
            if ss.member:
                bonus = next(t["trade_bonus"] for t in C.MEMBERSHIP_TIERS if t["name"] == ss.member["tier"])
                st.info(f"As a {ss.member['tier']} member you'll get an extra {bonus}% "
                        "when you take store credit.")


# --------------------------------------------------------------------------
# Navigation
# --------------------------------------------------------------------------
PAGES = {
    "home": st.Page(page_home, title="Home", icon="🏠", default=True, url_path="home"),
    "shop": st.Page(page_shop, title="Shop", icon="🛍️", url_path="shop"),
    "spin": st.Page(page_spin, title="Spin & Win", icon="🎡", url_path="spin"),
    "offers": st.Page(page_offers, title="Offers", icon="🏷️", url_path="offers"),
    "club": st.Page(page_club, title="CG Club", icon="⭐", url_path="club"),
    "visit": st.Page(page_visit, title="Visit & Sell", icon="📍", url_path="visit"),
}
nav = st.navigation(list(PAGES.values()), position="top")
nav.run()
footer()
