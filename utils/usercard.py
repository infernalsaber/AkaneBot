"""AniList user profile cards (About, Favourites and Friends), drawn with Pillow"""

import asyncio
import html
import io
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from utils.errors import AniListError

KINDS = ("about", "favourites", "friends")

# ============= FETCHING =============

FRIEND_COLS = 6
FRIEND_ROWS = 4

_USER_FIELDS = """
    avatar { large } bannerImage id name options { profileColor } about
    statistics {
      anime { count meanScore standardDeviation minutesWatched episodesWatched
              statuses { status count minutesWatched }
              genres(limit: 10, sort: COUNT_DESC) { genre count meanScore } }
      manga { count meanScore standardDeviation chaptersRead volumesRead
              statuses { status count }
              genres(limit: 10, sort: COUNT_DESC) { genre count meanScore } }
    }
    favourites {
      anime { pageInfo { total hasNextPage } edges { favouriteOrder node { id title { userPreferred } coverImage { large color } } } }
      manga { pageInfo { total hasNextPage } edges { favouriteOrder node { id title { userPreferred } format coverImage { large } } } }
      characters { pageInfo { total hasNextPage } edges { favouriteOrder node { name { userPreferred } image { large } media(sort: FAVOURITES_DESC, perPage: 1) { nodes { title { userPreferred } } } } } }
      staff { pageInfo { total hasNextPage } edges { favouriteOrder node { name { userPreferred } primaryOccupations image { large } } } }
      studios { pageInfo { total hasNextPage } edges { favouriteOrder node { name } } }
    }"""

_SCORES = "lists { entries { mediaId score(format: POINT_100) } }"

_MUTUALS = f"""
  mutuals: Page(perPage: {FRIEND_COLS * FRIEND_ROWS}) {{
    pageInfo {{ total }}
    mutualFollowers(userId: $id, sort: USERNAME) {{ id name avatar {{ large }} }}
  }}"""

# Everything the three cards need in one request. Mutuals need the numeric id,
# so they're only included when it's known.
_BY_ID = f"""query ($id: Int!) {{
  User(id: $id) {{{_USER_FIELDS}
  }}
  animeScores: MediaListCollection(userId: $id, type: ANIME) {{ {_SCORES} }}
  mangaScores: MediaListCollection(userId: $id, type: MANGA) {{ {_SCORES} }}{_MUTUALS}
}}"""

_BY_NAME = f"""query ($name: String) {{
  User(name: $name) {{{_USER_FIELDS}
  }}
  animeScores: MediaListCollection(userName: $name, type: ANIME) {{ {_SCORES} }}
  mangaScores: MediaListCollection(userName: $name, type: MANGA) {{ {_SCORES} }}
}}"""

_MUTUALS_ONLY = f"query ($id: Int!) {{{_MUTUALS}\n}}"

# username (lowercase) -> AniList id, so repeat lookups by name take one request
_ids: dict[str, int] = {}


async def fetch_profile(client, user: str) -> dict | None:
    """Fetch everything the cards need for a user (by name or id)

    One request when the id is known (numeric input or a name seen before);
    a name seen for the first time needs a second, small one for the mutuals.
    None if the user doesn't exist (or AniList is down).
    """
    user_id = int(user) if user.isdigit() else _ids.get(user.lower())
    try:
        if user_id is not None:
            data = await client.query(_BY_ID, {"id": user_id}, partial=True)
        else:
            data = await client.query(_BY_NAME, {"name": user}, partial=True)
        profile = data.get("User")
        if not profile:
            return None
        _ids[profile["name"].lower()] = profile["id"]
        if "mutuals" not in data:
            data.update(await client.query(_MUTUALS_ONLY, {"id": profile["id"]}, partial=True))
    except AniListError:
        return None

    # Favourites in the user's own order (as on the site)
    for fav in profile["favourites"].values():
        edges = sorted(fav.get("edges") or [], key=lambda e: e["favouriteOrder"])
        fav["nodes"] = [e["node"] for e in edges]

    # The user's own rating on their favourite anime/manga (null if their lists are private)
    for kind in ("anime", "manga"):
        lists = (data.get(f"{kind}Scores") or {}).get("lists") or []
        scores = {e["mediaId"]: e["score"] for lst in lists for e in lst["entries"]}
        for node in profile["favourites"][kind]["nodes"]:
            node["userScore"] = scores.get(node["id"])

    mutuals = data.get("mutuals") or {}
    profile["mutuals"] = mutuals.get("mutualFollowers") or []
    profile["mutualCount"] = (mutuals.get("pageInfo") or {}).get("total") or len(profile["mutuals"])
    return profile


def _image_urls(kind: str, user: dict) -> set[str]:
    """The images one card draws: the header's plus that card's own"""
    urls = {user.get("bannerImage"), (user.get("avatar") or {}).get("large")}
    fav = user["favourites"]
    if kind == "favourites":
        urls |= {n["coverImage"]["large"] for n in fav["anime"]["nodes"] + fav["manga"]["nodes"]}
        urls |= {n["image"]["large"] for n in fav["characters"]["nodes"] + fav["staff"]["nodes"]}
    elif kind == "friends":
        urls |= {(f.get("avatar") or {}).get("large") for f in user["mutuals"]}
    return {url for url in urls if url}


async def _download(session, url: str) -> bytes | None:
    try:
        resp = await session.get(url, timeout=15)
        return await resp.read() if resp.ok else None
    except Exception:
        return None


async def render_card(kind: str, user: dict, session) -> bytes:
    """Download a card's images, then draw it to PNG bytes off the event loop"""
    urls = list(_image_urls(kind, user))
    downloads = await asyncio.gather(*(_download(session, url) for url in urls))
    images = {url: data for url, data in zip(urls, downloads) if data}
    return await asyncio.to_thread(_render, kind, user, images)


async def render_skeleton(kind: str, user: dict) -> bytes:
    """Draw a card with flat boxes where the images go (nothing to download)"""
    return await asyncio.to_thread(_render, kind, user, None)


def _render(kind: str, user: dict, images: dict[str, bytes] | None) -> bytes:
    render = {"about": render_about, "favourites": render_favourites, "friends": render_friends}[kind]
    buf = io.BytesIO()
    render(user, images).save(buf, format="PNG")
    return buf.getvalue()


# ============= DRAWING HELPERS =============

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
OVERPASS = FONT_DIR / "Overpass-VariableFont_wght.ttf"
ROBOTO = FONT_DIR / "Roboto-VariableFont_wdth,wght.ttf"

W = 1080
BANNER_H = 277
BG = (10, 20, 32)
TEXT = (235, 241, 250)
MUTED = (132, 150, 172)
CARD = (18, 32, 48)
SKELETON_FILL = (30, 44, 62)
DEFAULT_ACCENT = (232, 245, 106)

# AniList profileColor names -> hex
PROFILE_COLORS = {
    "blue": "#3db4f2", "purple": "#c063ff", "pink": "#fc9dd6", "orange": "#ef881a",
    "red": "#e13333", "green": "#4cca51", "gray": "#677b94",
}


def font(path: Path, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    try:
        f = ImageFont.truetype(str(path), size)
        # both fonts list weight first; Roboto adds a width axis (100 = normal)
        f.set_variation_by_axes([weight, 100] if len(f.get_variation_axes()) == 2 else [weight])
        return f
    except OSError:
        return ImageFont.load_default(size)


def hex_to_rgb(value: str | None, default=DEFAULT_ACCENT) -> tuple[int, int, int]:
    if not value:
        return default
    value = PROFILE_COLORS.get(value, value).lstrip("#")
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def accent_of(user: dict) -> tuple[int, int, int]:
    return hex_to_rgb((user.get("options") or {}).get("profileColor"))


def placeholder(size: tuple[int, int], seed: str, base: tuple[int, int, int] | None = None) -> Image.Image:
    """Soft gradient + blobs, the same for the same seed. Drawn when an image is missing."""
    rnd = random.Random(seed)
    base = base or tuple(rnd.randint(70, 200) for _ in range(3))
    w, h = size
    img = Image.new("RGB", size, base)
    d = ImageDraw.Draw(img)
    for y in range(h):  # vertical darkening
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c * (1 - 0.55 * t)) for c in base))
    for _ in range(5):
        r = rnd.randint(max(w, h) // 8, max(w, h) // 3)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        col = tuple(min(255, c + rnd.randint(-40, 80)) for c in base)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    return img.filter(ImageFilter.GaussianBlur(max(w, h) // 14))


def cover(images: dict[str, bytes] | None, src: str | None, size: tuple[int, int], seed: str,
          color: str | None = None) -> Image.Image:
    """The image at `src`, cover-cropped to `size`

    `images` is None for skeletons (a flat box); a missing image gets a placeholder.
    """
    if images is None:
        return Image.new("RGB", size, SKELETON_FILL)
    try:
        img = Image.open(io.BytesIO(images[src])).convert("RGB")
    except Exception:
        img = placeholder(size, seed, hex_to_rgb(color, default=None) if color else None)
    sw, sh = img.size
    scale = max(size[0] / sw, size[1] / sh)
    img = img.resize((max(1, round(sw * scale)), max(1, round(sh * scale))), Image.LANCZOS)
    left, top = (img.width - size[0]) // 2, (img.height - size[1]) // 2
    return img.crop((left, top, left + size[0], top + size[1]))


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *img.size], radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def fit(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_w: int) -> str:
    """`text` cut with an ellipsis to fit in `max_w`"""
    if draw.textlength(text, font=f) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=f) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def draw_header(img: Image.Image, user: dict, images: dict[str, bytes] | None) -> None:
    """Banner, avatar and username (on a dark scrim at the banner's bottom edge)"""
    img.paste(cover(images, user.get("bannerImage"), (W, BANNER_H), "banner", "#f0b6cf"), (0, 0))
    scrim = Image.new("RGBA", (W, 130))
    sd = ImageDraw.Draw(scrim)
    for i in range(130):
        sd.line([(0, i), (W, i)], fill=(8, 14, 22, int(200 * (i / 129) ** 1.5)))
    img.paste(scrim, (0, BANNER_H - 130), scrim)
    ImageDraw.Draw(img).text((284, BANNER_H - 19), user["name"], font=font(OVERPASS, 52, 800),
                             fill=TEXT, anchor="ls")
    avatar = rounded(cover(images, (user.get("avatar") or {}).get("large"), (192, 192), "avatar"), 22)
    img.paste(avatar, (60, 84), avatar)


# ============= ABOUT CARD =============

ABOUT_CHARS = 160
MAX_NEWLINES = 5  # bio keeps at most this many line breaks
# genre chip / bar-segment colours, in rank order
GENRE_COLORS = [(96, 214, 53), (0, 168, 255), (145, 85, 240), (250, 120, 160),
                (235, 95, 115), (250, 160, 100)]
LABELLED_GENRES = 4  # genres shown as chips; the bar shows up to len(GENRE_COLORS)

# AniList markup: img###(url), webm(url), youtube(url), ~~~centered~~~, ~!spoilers!~,
# plus regular markdown and the odd bit of raw HTML
_EMBED = re.compile(r"\b(?:img\d*%?|webm|youtube|video)\([^)]*\)", re.I)
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_SPOILER = re.compile(r"~!.*?!~", re.S)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_URL = re.compile(r"https?://\S+")
_EMPHASIS = re.compile(r"(\*\*|__|\*|(?<!\w)_)(.+?)\1", re.S)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def clean_about(raw: str | None, limit: int = ABOUT_CHARS) -> str:
    """Strip embeds/markup from an AniList bio and return its first ~`limit` characters"""
    text = html.unescape(raw or "").replace("\r", "")
    for pat in (_SPOILER, _EMBED, _MD_IMAGE):
        text = pat.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    text = _URL.sub("", text)
    text = text.replace("~~~", "")
    text = _EMPHASIS.sub(r"\2", text)
    text = re.sub(r"^\s{0,3}(?:#{1,6}\s*|>\s?|[-*+]\s+(?=\S)|-{3,}\s*$)", "", text, flags=re.M)
    text = _EMOJI.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    lines = text.split("\n")
    if len(lines) > MAX_NEWLINES + 1:
        text = "\n".join(lines[: MAX_NEWLINES + 1]).rstrip(" ,.;:-\n")
        if len(text) <= limit:
            return text + "…"
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut[limit // 2:]:  # don't slice a word in half
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,.;:-\n") + "…"


def wrap_paragraphs(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> list[str]:
    """Greedy word wrap that keeps the author's line breaks ('' marks a paragraph gap)"""
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}".strip()
            if d.textlength(trial, font=f) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def icon(kind: str, size: int, fg, bg) -> Image.Image:
    """Round badge with a simple vector glyph, drawn 4x and downsampled for smooth edges"""
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(im)
    g.ellipse([0, 0, S - 1, S - 1], fill=bg)
    u = S / 100  # glyph coordinates are 0..100

    def P(*pts):
        return [(x * u, y * u) for x, y in pts]

    def line(a, b, w):
        g.line(P(a, b), fill=fg, width=round(w * u))

    def dot(cx, cy, r):
        g.ellipse([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], fill=fg)

    if kind == "monitor":
        g.rounded_rectangle([30 * u, 32 * u, 70 * u, 60 * u], 4 * u, fill=fg)
        g.rounded_rectangle([34 * u, 36 * u, 66 * u, 56 * u], 2 * u, fill=bg)
        line((50, 60), (50, 67), 5)
        line((40, 67), (60, 67), 5)
    elif kind == "play":
        g.polygon(P((39, 30), (39, 70), (70, 50)), fill=fg)
    elif kind == "calendar":
        g.rounded_rectangle([30 * u, 33 * u, 70 * u, 70 * u], 6 * u, fill=fg)
        g.rectangle(P((38, 28), (43, 38)), fill=fg)
        g.rectangle(P((57, 28), (62, 38)), fill=fg)
        for row in (50, 60):
            for col in (36, 46, 56):
                g.rectangle(P((col, row), (col + 6, row + 5)), fill=bg)
    elif kind == "percent":
        line((63, 32), (37, 68), 6)
        dot(38, 38, 7)
        dot(62, 62, 7)
    elif kind == "book":
        g.polygon(P((48, 37), (31, 32), (31, 67), (48, 72)), fill=fg)
        g.polygon(P((52, 37), (69, 32), (69, 67), (52, 72)), fill=fg)
    elif kind == "list":
        for yy in (36, 50, 64):
            dot(34, yy, 3.5)
            line((43, yy), (68, yy), 5)
    elif kind == "layers":
        for top in (31, 45, 59):
            g.rounded_rectangle([30 * u, top * u, 70 * u, (top + 10) * u], 3 * u, fill=fg)
    return im.resize((size, size), Image.LANCZOS)


def render_about(user: dict, images: dict[str, bytes] | None) -> Image.Image:
    """Bio excerpt, a combined genre overview and watch/read stats"""
    accent = accent_of(user)
    img = Image.new("RGB", (W, 2400), BG)
    draw_header(img, user, images)
    d = ImageDraw.Draw(img)

    f_label = font(OVERPASS, 22, 800)
    f_body = font(ROBOTO, 22, 400)
    f_small = font(ROBOTO, 20, 400)
    f_count = font(ROBOTO, 18, 600)
    f_entries = font(ROBOTO, 15, 400)
    f_chip = font(ROBOTO, 20, 500)

    left, right = 60, W - 60
    full_w = right - left

    def heading(x, y, width, label, note=None):
        d.text((x, y), label, font=f_label, fill=accent)
        if note:
            d.text((x + width, y + 3), note, font=f_small, fill=MUTED, anchor="ra")
        d.line([(x, y + 34), (x + width, y + 34)], fill=CARD, width=3)
        return y + 54

    y = BANNER_H + 36

    # --- bio
    bio = clean_about(user.get("about"))
    if bio:
        y = heading(left, y, full_w, "ABOUT", f"first {ABOUT_CHARS} characters" if bio.endswith("…") else None)
        pad, line_h = 22, 32
        lines = wrap_paragraphs(d, bio, f_body, full_w - 2 * pad)
        box_h = 2 * pad + sum(line_h if ln else line_h // 2 for ln in lines)
        d.rounded_rectangle([left, y, right, y + box_h], 20, fill=CARD)
        ty = y + pad
        for ln in lines:
            if ln:
                d.text((left + pad, ty), ln, font=f_body, fill=TEXT)
            ty += line_h if ln else line_h // 2
        y += box_h + 36

    # --- per-type stats (types with no entries are skipped)
    stats = user["statistics"]
    cols = []  # (label, [(icon, value, caption)], genres)
    a = stats.get("anime") or {}
    if a.get("count"):
        cols.append(("ANIME", [
            ("monitor", str(int(a["count"] or 0)), "Total"),
            ("play", str(int(a["episodesWatched"] or 0)), "Episodes"),
            ("calendar", f"{a['minutesWatched'] / 1440:.1f}", "Days"),
            ("percent", f"{a['meanScore']:.1f}", "Mean Score"),
        ], a.get("genres") or []))
    m = stats.get("manga") or {}
    if m.get("count"):
        cols.append(("MANGA", [
            ("book", str(int(m["count"] or 0)), "Total"),
            ("list", str(int(m["chaptersRead"] or 0)), "Chapters"),
            ("layers", str(int(m["volumesRead"] or 0)), "Volumes"),
            ("percent", f"{m['meanScore']:.1f}", "Mean Score"),
        ], m.get("genres") or []))

    # --- genre overview: anime + manga merged, chips for the top few, proportional bar below
    merged: dict[str, int] = {}
    for _, _, genres in cols:
        for g in genres:
            merged[g["genre"]] = merged.get(g["genre"], 0) + g["count"]
    top = sorted(merged.items(), key=lambda kv: -kv[1])[:len(GENRE_COLORS)]
    if top:
        y = heading(left, y, full_w, "GENRE OVERVIEW")
        panel_h, bar_h = 132, 16
        d.rounded_rectangle([left, y, right, y + panel_h], 20, fill=CARD)
        slot = full_w / LABELLED_GENRES
        for i, (name, count) in enumerate(top[:LABELLED_GENRES]):
            color = GENRE_COLORS[i]
            cx = left + slot * (i + 0.5)
            tw = int(d.textlength(name, font=f_chip)) + 44
            d.rounded_rectangle([cx - tw / 2, y + 24, cx + tw / 2, y + 24 + 38], 8, fill=color)
            d.text((cx, y + 24 + 19), name, font=f_chip, fill=(255, 255, 255), anchor="mm")
            nw = d.textlength(f"{count:,}", font=f_count)
            ew = d.textlength(" Entries", font=f_entries)
            x0 = cx - (nw + ew) / 2
            d.text((x0, y + 84), f"{count:,}", font=f_count, fill=color, anchor="lm")
            d.text((x0 + nw, y + 85), " Entries", font=f_entries, fill=MUTED, anchor="lm")
        # segmented bar, clipped to the panel's rounded bottom corners
        strip = Image.new("RGB", (full_w, bar_h))
        sd = ImageDraw.Draw(strip)
        total = sum(c for _, c in top)
        sx = 0.0
        for i, (_, count) in enumerate(top):
            nx = sx + full_w * count / total
            sd.rectangle([round(sx), 0, round(nx), bar_h], fill=GENRE_COLORS[i])
            sx = nx
        mask = Image.new("L", (full_w, panel_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, full_w - 1, panel_h - 1], 20, fill=255)
        mask = mask.crop((0, panel_h - bar_h, full_w, panel_h))
        img.paste(strip, (left, y + panel_h - bar_h), mask)
        y += panel_h + 44

    # --- stat rows with round icon badges: 2 x 2 per type, or 4 in a row when there's one type
    gap = 40
    col_w = full_w if len(cols) == 1 else (full_w - gap) // 2
    per_row = 4 if len(cols) == 1 else 2
    cell_w, row_h, badge = col_w // per_row, 104, 64
    f_num = font(OVERPASS, 42, 800)
    f_caption = font(OVERPASS, 21, 700)
    end_y = y
    for i, (label, items, _) in enumerate(cols):
        x = left + i * (col_w + gap)
        cy = heading(x, y, col_w, label)
        for t, (kind, value, caption) in enumerate(items):
            tx = x + (t % per_row) * cell_w
            ty = cy + (t // per_row) * row_h
            b = icon(kind, badge, (150, 165, 186), CARD)
            img.paste(b, (tx, ty + 4), b)
            d.text((tx + badge + 16, ty - 2), value, font=f_num, fill=accent)
            d.text((tx + badge + 16, ty + 52), caption, font=f_caption, fill=MUTED)
        end_y = max(end_y, cy + ((len(items) + per_row - 1) // per_row) * row_h)

    return img.crop((0, 0, W, end_y + 40))


# ============= FAVOURITES CARD =============


def render_favourites(user: dict, images: dict[str, bytes] | None) -> Image.Image:
    """Grids of favourite anime, manga, characters and staff, then a strip of studios"""
    fav = user["favourites"]
    accent = accent_of(user)
    img = Image.new("RGB", (W, 2000), BG)
    d = ImageDraw.Draw(img)
    draw_header(img, user, images)

    f_label = font(OVERPASS, 22, 800)
    f_pill = font(ROBOTO, 22, 600)
    f_item = font(ROBOTO, 20, 500)
    f_sub_item = font(ROBOTO, 17, 400)
    f_badge = font(ROBOTO, 18, 700)

    # AniList-style grids: sections flow two per row; empty ones are skipped and a
    # lone section on its row stretches to full width (6 covers)
    inner_l, inner_r = 60, W - 60
    sec_gap, cgap, row_gap = 40, 22, 24
    sec_w = (inner_r - inner_l - sec_gap) // 2
    cw = (sec_w - cgap * 2) // 3
    ch = round(cw * 1.5)

    def wrap(text: str, max_w: int, lines: int = 2) -> list[str]:
        out, cur = [], ""
        for word in text.split():
            if d.textlength((cur + " " + word).strip(), font=f_item) <= max_w:
                cur = (cur + " " + word).strip()
            else:
                out.append(cur)
                cur = word
        out.append(cur)
        out = [o for o in out if o]
        if len(out) > lines:
            # cut the overflow mid-word instead of dropping whole words
            out = out[:lines - 1] + [fit(d, " ".join(out[lines - 1:]), f_item, max_w)]
        return [fit(d, o, f_item, max_w) for o in out]

    def grid(items, cols, rows):
        """Split items into at most `rows` rows of `cols`; empty rows are dropped"""
        return [r for r in (items[k * cols:(k + 1) * cols] for k in range(rows)) if r]

    def cover_row_height(row):
        lines = max((len(wrap(i[0], cw)) for i in row), default=1)
        sub = 22 if any(i[4] for i in row) else 0
        return ch + 8 + lines * 25 + sub

    def section_height(items, cols, rows=1):
        heights = [cover_row_height(r) for r in grid(items, cols, rows)] or [cover_row_height([])]
        return 48 + sum(heights) + row_gap * (len(heights) - 1) + 34

    def heading(x, y, width, label, key):
        # AniList's total is only accurate on the last page, so past one page it's "25+"
        page = fav[key]["pageInfo"]
        total = f"{len(fav[key]['nodes'])}+" if page.get("hasNextPage") else page["total"]
        d.text((x, y), label, font=f_label, fill=accent)
        d.text((x + width, y + 2), f"{total} total", font=f_pill, fill=MUTED, anchor="ra")
        d.line([(x, y + 34), (x + width, y + 34)], fill=CARD, width=3)

    def section(x, y, width, label, key, items, cols, rows=1):
        heading(x, y, width, label, key)
        iy = y + 48
        for row in grid(items, cols, rows):
            for i, (name, src, color, badge, sub) in enumerate(row):
                ix = x + i * (cw + cgap)
                c_img = rounded(cover(images, src, (cw, ch), name, color), 10)
                img.paste(c_img, (ix, iy), c_img)
                if badge:
                    bw = int(d.textlength(badge, font=f_badge)) + 14
                    d.rounded_rectangle([ix + 6, iy + ch - 30, ix + 6 + bw, iy + ch - 6], 12, fill=accent)
                    d.text((ix + 13, iy + ch - 18), badge, font=f_badge, fill=BG, anchor="lm")
                lines = wrap(name, cw)
                for j, line in enumerate(lines):
                    d.text((ix, iy + ch + 8 + j * 25), line, font=f_item, fill=TEXT)
                if sub:
                    d.text((ix, iy + ch + 8 + len(lines) * 25 + 1), fit(d, sub, f_sub_item, cw),
                           font=f_sub_item, fill=MUTED)
            iy += cover_row_height(row) + row_gap

    def score(n):
        """The profile owner's own rating (0-100), if they've scored the title"""
        return str(n["userScore"]) if n.get("userScore") else None

    def first_media(n):
        m = ((n.get("media") or {}).get("nodes") or [None])[0]
        return m["title"]["userPreferred"] if m else None

    # Each item: (name, image, placeholder colour, badge, subtitle)
    sections = [
        ("ANIME", "anime", [(n["title"]["userPreferred"], n["coverImage"]["large"],
                             n["coverImage"].get("color"), score(n), None)
                            for n in fav["anime"]["nodes"]]),
        ("MANGA", "manga", [(n["title"]["userPreferred"], n["coverImage"]["large"], None, score(n), None)
                            for n in fav["manga"]["nodes"]]),
        ("CHARACTERS", "characters", [(n["name"]["userPreferred"], n["image"]["large"], None, None,
                                       first_media(n)) for n in fav["characters"]["nodes"]]),
        ("STAFF", "staff", [(n["name"]["userPreferred"], n["image"]["large"], None, None,
                             ", ".join((n.get("primaryOccupations") or [])[:1]) or None)
                            for n in fav["staff"]["nodes"]]),
    ]
    # Anime pairs only with manga, characters only with staff. A section alone in its pair
    # takes the full width (6 covers); if a whole pair is empty the other pair's sections
    # stack on their own full-width rows; a single section overall gets two rows (12 covers)
    by_key = {sec[1]: sec for sec in sections if sec[2]}
    pairs = [[by_key[k] for k in pair if k in by_key]
             for pair in (("anime", "manga"), ("characters", "staff"))]
    pairs = [p for p in pairs if p]
    rows = [[pairs[0][0]], [pairs[0][1]]] if len(pairs) == 1 and len(pairs[0]) == 2 else pairs
    cover_rows = 2 if len(rows) == 1 and len(rows[0]) == 1 else 1

    y = 320
    for row in rows:
        if len(row) == 1:
            label, key, items = row[0]
            section(inner_l, y, inner_r - inner_l, label, key, items, 6, cover_rows)
            y += section_height(items, 6, cover_rows)
        else:
            (l1, k1, i1), (l2, k2, i2) = row
            section(inner_l, y, sec_w, l1, k1, i1, 3)
            section(inner_l + sec_w + sec_gap, y, sec_w, l2, k2, i2, 3)
            y += max(section_height(i1, 3), section_height(i2, 3))

    # --- studios, as pills that wrap onto new lines
    bottom = y + 30
    studios = fav["studios"]["nodes"]
    if studios:
        heading(inner_l, y, inner_r - inner_l, "STUDIOS", "studios")
        px, py = inner_l, y + 48
        for node in studios:
            w = int(d.textlength(node["name"], font=f_pill)) + 28
            if px + w > inner_r:
                px, py = inner_l, py + 46
            h = f_pill.size + 14
            d.rounded_rectangle([px, py, px + w, py + h], h // 2, fill=CARD)
            d.text((px + 14, py + h // 2), node["name"], font=f_pill, fill=TEXT, anchor="lm")
            px += w + 10
        bottom = py + 36 + 50

    return img.crop((0, 0, W, bottom))


# ============= FRIENDS CARD =============


def render_friends(user: dict, images: dict[str, bytes] | None) -> Image.Image:
    """A grid of the user's mutual followers (avatar + username)"""
    accent = accent_of(user)
    img = Image.new("RGB", (W, 1600), BG)
    d = ImageDraw.Draw(img)
    draw_header(img, user, images)

    f_label = font(OVERPASS, 22, 800)
    f_pill = font(ROBOTO, 22, 600)
    f_name = font(ROBOTO, 19, 500)

    left, right = 60, W - 60
    gap = 24
    tile = (right - left - gap * (FRIEND_COLS - 1)) // FRIEND_COLS
    row_h = tile + 10 + 26 + gap

    y = BANNER_H + 36
    count = user["mutualCount"]
    d.text((left, y), "FRIENDS", font=f_label, fill=accent)
    d.text((right, y + 2), f"{count} mutual{'s' if count != 1 else ''}", font=f_pill, fill=MUTED, anchor="ra")
    d.line([(left, y + 34), (right, y + 34)], fill=CARD, width=3)
    y += 54

    if not user["mutuals"]:
        d.rounded_rectangle([left, y, right, y + 90], 20, fill=CARD)
        d.text(((left + right) // 2, y + 45), "No mutual followers yet", font=f_pill, fill=MUTED,
               anchor="mm")
        return img.crop((0, 0, W, y + 90 + 40))

    for i, friend in enumerate(user["mutuals"]):
        tx = left + (i % FRIEND_COLS) * (tile + gap)
        ty = y + (i // FRIEND_COLS) * row_h
        avatar = rounded(cover(images, (friend.get("avatar") or {}).get("large"), (tile, tile), friend["name"]), 14)
        img.paste(avatar, (tx, ty), avatar)
        d.text((tx + tile // 2, ty + tile + 10), fit(d, friend["name"], f_name, tile), font=f_name,
               fill=TEXT, anchor="ma")

    rows = (len(user["mutuals"]) + FRIEND_COLS - 1) // FRIEND_COLS
    return img.crop((0, 0, W, y + rows * row_h - gap + 40))
