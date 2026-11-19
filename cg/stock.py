"""Live St Helens stock from the public Shopify collection feed."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .config import STORE

FEED = STORE["collection_url"] + "/products.json"
SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "stock_snapshot.json"

# Ordered: first match wins.
CATEGORY_RULES = [
    ("Gaming", r"xbox|playstation|ps[45p]\b|psp|nintendo|switch|game ?boy|quest|oculus|"
               r"borderlands|ghostbusters|minecraft|poppy playtime|video game|controller"),
    ("Tablets", r"\bipad\b|galaxy tab|\btablet\b|kindle"),
    ("Phones", r"iphone|galaxy [asz]\d|galaxy note|pixel|honor|motorola|oneplus|xiaomi|\bphone\b"),
    ("Cameras", r"canon|nikon|sony a\d|fujifilm|gopro|dji|lens|tripod|camera|gimbal"),
    ("Computing", r"laptop|macbook|\bhp \d|lenovo|dell|thinkpad|ssd|\bram\b|power supply|monitor"),
    ("Watches & Jewellery", r"watch|gold|\brings?\b|necklace|bracelet|chain|earring"),
    ("Collectables", r"lego|signed|statue|cgc|pokemon| ex\b|holo|funko|comic|figure|enchanted"),
    ("Sports & Leisure", r"fishing|bite alarm|golf|bike|cycle|weights|gym"),
    ("Home & DIY", r"measure|level|drill|vacuum|tool|kitchen"),
]
CATEGORY_ICONS = {
    "Phones": "📱", "Tablets": "📲", "Gaming": "🎮", "Cameras": "📷",
    "Computing": "💻", "Watches & Jewellery": "⌚", "Collectables": "🏆",
    "Sports & Leisure": "🎣", "Home & DIY": "🛠️", "Other": "🛍️",
}

PLACEHOLDER = "placeholder"


@dataclass
class Product:
    id: int
    title: str
    handle: str
    price: float
    was: float | None
    available: bool
    category: str
    condition: str
    images: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    published: str = ""
    description: str = ""

    @property
    def url(self) -> str:
        return STORE["product_url"].format(handle=self.handle)

    @property
    def saving(self) -> float:
        return round(self.was - self.price, 2) if self.was and self.was > self.price else 0.0

    @property
    def saving_pct(self) -> int:
        return round(100 * self.saving / self.was) if self.saving else 0

    @property
    def image(self) -> str | None:
        return self.images[0] if self.images else None

    def member_price(self, pct: float) -> float:
        return round(self.price * (1 - pct / 100), 2)


def _clean_title(t: str) -> str:
    t = re.sub(r"\s+", " ", t.replace("\t", " ")).strip()
    return t


def _categorise(title: str) -> str:
    low = title.lower()
    for name, pattern in CATEGORY_RULES:
        if re.search(pattern, low):
            return name
    return "Other"


def _condition(tags: list[str]) -> str:
    for t in tags:
        if t.startswith("Pre-Owned: Grade"):
            return t.replace("Pre-Owned: ", "")  # "Grade A"
    if "New" in tags:
        return "New"
    if "New Other" in tags:
        return "New (open box)"
    return "Pre-owned"


def _sized(src: str, width: int = 600) -> str:
    if src.startswith("//"):
        src = "https:" + src
    joiner = "&" if "?" in src else "?"
    return f"{src}{joiner}width={width}"


def _strip_html(s: str | None) -> str:
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"&amp;", "&", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def parse(raw: list[dict]) -> list[Product]:
    out = []
    for p in raw:
        v = (p.get("variants") or [{}])[0]
        price = float(v.get("price") or 0)
        was = v.get("compare_at_price")
        was = float(was) if was else None
        imgs = [_sized(i["src"]) for i in p.get("images", []) if PLACEHOLDER not in i["src"]]
        title = _clean_title(p["title"])
        out.append(Product(
            id=p["id"], title=title, handle=p["handle"], price=price, was=was,
            available=bool(v.get("available", True)), category=_categorise(title),
            condition=_condition(p.get("tags", [])), images=imgs, tags=p.get("tags", []),
            published=p.get("published_at") or "", description=_strip_html(p.get("body_html")),
        ))
    return out


def fetch_live(timeout: float = 8) -> list[dict]:
    """Every product in the St Helens collection (paginated)."""
    products, page = [], 1
    while page <= 20:
        r = requests.get(FEED, params={"limit": 250, "page": page}, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0 (CG St Helens app)"})
        r.raise_for_status()
        batch = r.json().get("products", [])
        if not batch:
            break
        products += batch
        if len(batch) < 250:
            break
        page += 1
    return products


def load_snapshot() -> tuple[list[dict], str]:
    data = json.loads(SNAPSHOT.read_text())
    return data["products"], data.get("captured", "")


def load_stock() -> tuple[list[Product], str]:
    """Returns (products, source description). Falls back to the bundled snapshot."""
    try:
        raw = fetch_live()
        if raw:
            return parse(raw), "live"
    except (requests.RequestException, ValueError):
        pass
    raw, captured = load_snapshot()
    return parse(raw), f"snapshot {captured}"
