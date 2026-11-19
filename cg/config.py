"""Store settings and promotions.

Everything customer-facing that the St Helens team may want to change lives
here: store details, the spin-the-wheel prizes, monthly offers and the
membership tiers. Edit, save and the app picks it up on the next reload.
"""

# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------
STORE = {
    "name": "Cash Generator St Helens",
    "short": "St Helens",
    "address": "41 Church Street, St Helens, WA10 1AX",
    "store_page": "https://cashgenerator.co.uk/pages/st-helens",
    "collection_url": "https://cashgenerator.co.uk/collections/st-helens",
    "product_url": "https://cashgenerator.co.uk/products/{handle}",
    "email": "customerenquiries@cashgenerator.co.uk",
    # Fill these in to show a "Call" / "WhatsApp" button and opening hours.
    # Leave as None to send customers to the store page instead.
    "phone": None,  # e.g. "01744 000000"
    "whatsapp": None,  # e.g. "7700900000" (UK number without the leading 0)
    "hours": None,  # e.g. {"Mon–Sat": "9:00–17:30", "Sun": "10:00–16:00"}
    "logo": "https://cashgenerator.co.uk/cdn/shop/files/Cash_Generator_CMYK_ff39c41f-ea00-47f5-ab6a-f3db801c59cd-removebg-preview_460x.png?v=1688862651",
}

# Brand palette taken from cashgenerator.co.uk
BLUE = "#0033A0"
NAVY = "#024287"
YELLOW = "#FFB81C"

# --------------------------------------------------------------------------
# Spin the wheel
# --------------------------------------------------------------------------
# weight = relative chance. Prizes with a code_prefix issue a voucher code.
WHEEL_PRIZES = [
    {"label": "5% OFF", "detail": "5% off any pre-owned item", "weight": 30, "code_prefix": "SPIN5"},
    {"label": "£5 OFF", "detail": "£5 off when you spend £50+", "weight": 22, "code_prefix": "FIVER"},
    {"label": "TRY AGAIN", "detail": "No luck this time — spin again tomorrow!", "weight": 18, "code_prefix": None},
    {"label": "10% OFF", "detail": "10% off any pre-owned item", "weight": 12, "code_prefix": "SPIN10"},
    {"label": "+10% TRADE", "detail": "Extra 10% on your next trade-in", "weight": 10, "code_prefix": "TRADE10"},
    {"label": "FREE CASE", "detail": "Free phone case with any phone", "weight": 5, "code_prefix": "CASE"},
    {"label": "£20 OFF", "detail": "£20 off when you spend £150+", "weight": 2.5, "code_prefix": "BIG20"},
    {"label": "JACKPOT", "detail": "£50 off when you spend £200+", "weight": 0.5, "code_prefix": "JACKPOT"},
]
VOUCHER_VALID_DAYS = 14
VOUCHER_TERMS = (
    "One voucher per customer per transaction. Show this code in store or quote it when "
    "you call. Cannot be combined with other vouchers. Excludes gold, bullion and new items."
)

# --------------------------------------------------------------------------
# Offers
# --------------------------------------------------------------------------
# Always-on offers shown on the Offers page.
EVERGREEN_OFFERS = [
    {"icon": "💷", "title": "Top cash for your tech",
     "text": "Bring in phones, laptops, consoles and tablets — get paid on the spot."},
    {"icon": "🔁", "title": "Trade-in bonus",
     "text": "Take store credit instead of cash and get up to 10% more for your goods."},
    {"icon": "🤝", "title": "Buy back",
     "text": "Use your goods to get quick cash, then buy them back when you are ready."},
    {"icon": "💍", "title": "Gold & jewellery",
     "text": "We buy gold, silver and watches — free, no-obligation valuations in store."},
    {"icon": "🛡️", "title": "12-month warranty",
     "text": "Peace of mind on pre-owned electronics bought in store or online."},
    {"icon": "🕒", "title": "Shop now, pay later",
     "text": "Spread the cost of bigger buys online with pay-later options at checkout."},
]

# One themed campaign per month (1 = January). Shown automatically.
MONTHLY_OFFERS = {
    1: {"theme": "New Year, New Tech", "offers": [
        "10% off all pre-owned laptops",
        "Unwanted Christmas gifts? Extra 10% when you trade in for credit",
        "Fitness month: 15% off gym equipment & smart watches"]},
    2: {"theme": "Love Your Tech", "offers": [
        "15% off jewellery & watches",
        "2-for-£20 on pre-owned games",
        "Free screen protector with every phone"]},
    3: {"theme": "Spring Clear-Out", "offers": [
        "Bring 3+ items to sell and get a £5 bonus",
        "10% off garden & DIY tools",
        "Tablets from £49"]},
    4: {"theme": "Easter Game-On", "offers": [
        "3 games for £25",
        "£20 off consoles over £200",
        "Kids' tech: 10% off handhelds"]},
    5: {"theme": "Snap Happy May", "offers": [
        "15% off cameras & lenses",
        "Free memory card with any camera",
        "Drones from £79"]},
    6: {"theme": "Summer of Sound", "offers": [
        "15% off headphones & speakers",
        "Father's Day: 10% off watches",
        "Festival-ready phones from £59"]},
    7: {"theme": "Summer Holiday Deals", "offers": [
        "Travel tech: 10% off tablets & e-readers",
        "Keep the kids busy: 3 games for £25",
        "Extra 10% on trade-in for store credit"]},
    8: {"theme": "Back to School", "offers": [
        "Student laptops from £99",
        "10% off calculators, tablets & accessories with student ID",
        "Free laptop health check"]},
    9: {"theme": "Upgrade September", "offers": [
        "New iPhone out? Trade in your old one for a 15% credit boost",
        "£25 off flagship phones",
        "Free case with any smartphone"]},
    10: {"theme": "Spooktacular Savings", "offers": [
        "Horror games 3 for £20",
        "Collectables & cards: 10% off",
        "Spin the wheel twice on Halloween"]},
    11: {"theme": "Black Friday Month", "offers": [
        "Up to 30% off selected tech — see Price Drops below",
        "Members get 48-hour early access to Black Friday deals",
        "Extra 15% when you trade in for store credit"]},
    12: {"theme": "12 Deals of Christmas", "offers": [
        "A new deal every day 1–12 December",
        "Gift vouchers available in store",
        "Christmas cash: we'll beat any local valuation on gold"]},
}

# Weekly specials (0 = Monday).
DAILY_DEALS = {
    0: ("Mega Monday", "£10 off any phone over £100"),
    1: ("Tech Tuesday", "10% off laptops, tablets & computing"),
    2: ("Watch Wednesday", "10% off watches & jewellery"),
    3: ("Throwback Thursday", "Retro & collectables 10% off"),
    4: ("Fri-Yay Trade-In", "Extra 5% on all trade-ins today"),
    5: ("Gamer Saturday", "3 pre-owned games for £25"),
    6: ("Sunday Funday", "Double spins on the prize wheel"),
}

# --------------------------------------------------------------------------
# Membership ("CG Club")
# --------------------------------------------------------------------------
MEMBERSHIP_TIERS = [
    {"name": "Club Blue", "spend": 0, "discount": 5, "trade_bonus": 5, "colour": BLUE,
     "perks": ["5% off pre-owned items", "+5% on trade-ins for store credit",
               "Birthday treat voucher", "Members-only deal alerts"]},
    {"name": "Club Gold", "spend": 250, "discount": 10, "trade_bonus": 10, "colour": YELLOW,
     "perks": ["10% off pre-owned items", "+10% on trade-ins for store credit",
               "48h early access to sales", "Priority buy-back extensions"]},
    {"name": "Club Platinum", "spend": 750, "discount": 15, "trade_bonus": 15, "colour": "#5B6770",
     "perks": ["15% off pre-owned items", "+15% on trade-ins for store credit",
               "Free extended warranty on phones", "Reserve any item for 72 hours"]},
]
POINTS_PER_POUND = 1  # 1 point per £1 spent
POINTS_VALUE = 0.01  # each point worth 1p
