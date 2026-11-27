"""Meme/screenshot templates with user-supplied text, drawn with Pillow"""

import io
import json
import math
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from utils.usercard import FONT_DIR, font, hex_to_rgb

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"
# Per-template layout, fonts, colours and images; font paths are relative to FONT_DIR, images to TEMPLATE_DIR
TEMPLATES = json.loads((TEMPLATE_DIR / "templates.json").read_text())
# Site fonts (Chirp, gg sans) and Twemoji are kept locally here, gitignored
VENDOR_DIR = FONT_DIR / "vendor"
TWEMOJI_DIR = VENDOR_DIR / "twemoji"
CJK_FONTS = (
    VENDOR_DIR / "NotoSansCJK-Regular.ttc",
    Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
)
CJK = "\u2e80-\u9fff\uac00-\ud7af\uf900-\ufaff\uff00-\uffef"
# Wrap points: runs of spaces, single CJK characters, or any other unbroken run
TOKENS = re.compile(f"\\s+|[{CJK}]|[^\\s{CJK}]+")
VS16 = "\ufe0f"
CUSTOM_EMOJI = re.compile(r"<a?:(\w+):(\d+)>")
# Custom emoji stand in as Private Use Area characters, so wrapping and cutting treat each as one glyph
CUSTOM_BASE = 0xF0000
# Text is laid out and drawn at this scale, then shrunk: Pillow's hinting snaps small-size advances to whole pixels
SUPERSAMPLE = 4


def load_font(path: Path, size: float, weight: int = 400) -> ImageFont.FreeTypeFont:
    """Static fonts as-is; variable ones (the bundled fallbacks) at `weight`"""
    return font(path, size, weight) if "VariableFont" in path.name else ImageFont.truetype(str(path), size)


@cache
def cmap_of(path: Path) -> frozenset[int]:
    return frozenset(TTFont(path, fontNumber=0).getBestCmap())


@cache
def twemoji_index() -> tuple[dict[tuple[int, ...], Path], int]:
    """Twemoji files keyed by codepoints (VS16 dropped), and the longest key length"""
    index = {}
    for path in TWEMOJI_DIR.glob("*.png"):
        index[tuple(int(cp, 16) for cp in path.stem.split("-") if cp != "fe0f")] = path
    return index, max(map(len, index), default=0)


@cache
def emoji_image(path: Path, size: int) -> Image.Image:
    return Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def contained(img: Image.Image, size: int) -> Image.Image:
    """`img` scaled to fit a `size` square and centred in it, like Discord's object-fit: contain"""
    img = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    return tile


@dataclass
class RichFont:
    """A site font with a CJK fallback and inline Twemoji, laid out on one baseline"""

    path: Path
    size: float
    weight: int = 400
    # Emoji height, and how far its bottom sits below the baseline, both in em
    emoji_scale: float = 1.2
    emoji_drop: float = 0.25
    # Stand-in character -> custom emoji image
    custom: dict[str, Image.Image] = field(default_factory=dict)

    def __post_init__(self):
        self.main = load_font(self.path, self.size * SUPERSAMPLE, self.weight)
        cjk_path = next((path for path in CJK_FONTS if path.exists()), None)
        self.cjk = ImageFont.truetype(str(cjk_path), self.size * SUPERSAMPLE, index=0) if cjk_path else None
        self.cmap = cmap_of(self.path)
        self.ascent = self.main.getmetrics()[0] / SUPERSAMPLE
        self.emoji_px = round(self.size * self.emoji_scale)
        self.emoji_margin = self.size * 0.075

    def emoji_at(self, text: str, i: int) -> tuple[Path, int] | None:
        index, longest = twemoji_index()
        for end in range(min(len(text), i + longest), i, -1):
            key = tuple(ord(ch) for ch in text[i:end] if ch != VS16)
            # Text-style symbols (©, ®, ‼...) only become emoji when VS16 follows
            if len(key) == 1 and key[0] < 0x2100 and text[end:end + 1] != VS16:
                continue
            if key in index:
                while text[end:end + 1] == VS16:
                    end += 1
                return index[key], end
        return None

    def segments(self, text: str) -> list[tuple[str, ImageFont.FreeTypeFont | None]]:
        """Runs of (text, font); emoji come as (Twemoji path or custom image, None)"""
        runs: list[tuple[str, ImageFont.FreeTypeFont | None]] = []
        i = 0
        while i < len(text):
            if text[i] in self.custom:
                runs.append((self.custom[text[i]], None))
                i += 1
                continue
            emoji = self.emoji_at(text, i)
            if emoji:
                runs.append((emoji[0], None))
                i = emoji[1]
                continue
            ch = text[i]
            f = self.main if ord(ch) in self.cmap or not self.cjk or ch.isspace() else self.cjk
            if runs and runs[-1][1] is f:
                runs[-1] = (runs[-1][0] + ch, f)
            else:
                runs.append((ch, f))
            i += 1
        return runs

    def width(self, text: str) -> float:
        return sum(
            f.getlength(run) / SUPERSAMPLE if f else self.emoji_px + 2 * self.emoji_margin
            for run, f in self.segments(text)
        )

    def ellipsize(self, text: str, max_w: int) -> str:
        while text and self.width(f"{text}…") > max_w:
            text = text[:-1]
        return f"{text.rstrip()}…"

    def wrap(self, text: str, max_w: int, max_lines: int) -> list[str]:
        """Word wrap (per character for CJK and overlong words), cut with an ellipsis past `max_lines`"""
        lines: list[str] = []
        for para in text.split("\n"):
            cur = ""
            for token in TOKENS.findall(para):
                if self.width(cur + token) <= max_w:
                    cur += token
                    continue
                if cur.strip():
                    lines.append(cur.rstrip())
                cur = "" if token.isspace() else token
                while self.width(cur) > max_w:
                    cut = len(cur) - 1
                    while cut > 1 and self.width(cur[:cut]) > max_w:
                        cut -= 1
                    lines.append(cur[:cut])
                    cur = cur[cut:]
            lines.append(cur.strip())
            if len(lines) > max_lines:
                break
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self.ellipsize(lines[-1], max_w)
        return lines

    def draw(self, img: Image.Image, x: float, baseline: float, text: str, fill, shadow: int = 0) -> None:
        """`text` starting at `x` on `baseline`; `shadow` offsets a black copy of the text"""
        left, top = math.floor(x), math.floor(baseline - 2 * self.size)
        w, h = math.ceil(x - left + self.width(text)) + 2, math.ceil(3 * self.size)
        mask = Image.new("L", (w * SUPERSAMPLE, h * SUPERSAMPLE), 0)
        md = ImageDraw.Draw(mask)
        pen, base = (x - left) * SUPERSAMPLE, (baseline - top) * SUPERSAMPLE
        emojis = []
        for run, f in self.segments(text):
            if f is None:
                pen += self.emoji_margin * SUPERSAMPLE
                emojis.append((left + pen / SUPERSAMPLE, run))
                pen += (self.emoji_px + self.emoji_margin) * SUPERSAMPLE
                continue
            md.text((pen, base), run, font=f, fill=255, anchor="ls")
            pen += f.getlength(run)

        mask = mask.reduce(SUPERSAMPLE)
        if shadow:
            img.paste((0, 0, 0), (left + shadow, top + shadow, left + shadow + w, top + shadow + h), mask)
        img.paste(fill, (left, top, left + w, top + h), mask)
        emoji_y = round(baseline + self.size * self.emoji_drop - self.emoji_px)
        for emoji_x, source in emojis:
            emoji = emoji_image(source, self.emoji_px) if isinstance(source, Path) else contained(source, self.emoji_px)
            img.paste(emoji, (round(emoji_x), emoji_y), emoji)


def rich_font(font_cfg: dict, emoji_cfg: dict | None = None, size: float | None = None,
              custom: dict[str, Image.Image] | None = None) -> RichFont:
    """Font from config: its `file` if present (site fonts are optional), else `fallback`"""
    path = FONT_DIR / font_cfg["file"]
    if not path.exists():
        path = FONT_DIR / font_cfg["fallback"]
    emoji_cfg = emoji_cfg or {}
    return RichFont(
        path, size or font_cfg["size"], font_cfg.get("weight", 400),
        emoji_cfg.get("scale", 1.2), emoji_cfg.get("drop", 0.25), custom or {},
    )


def stretched(bg_path: Path, split_y: int, extra_h: int, fill) -> Image.Image:
    """Template with `extra_h` px of `fill` inserted at `split_y` (an empty band of the screenshot)"""
    bg = Image.open(bg_path).convert("RGB")
    w, h = bg.size
    img = Image.new("RGB", (w, h + extra_h), fill)
    img.paste(bg.crop((0, 0, w, split_y)), (0, 0))
    img.paste(bg.crop((0, split_y, w, h)), (0, split_y + extra_h))
    return img


def layout_body(body: dict, text: str, custom: dict[str, Image.Image]) -> tuple[RichFont, list[str], int]:
    """Font, wrapped lines, and the extra height the lines past the first need"""
    rf = rich_font(body["font"], body.get("emoji"), custom=custom)
    lines = rf.wrap(text, body["right"] - body["left"], body["max_lines"])
    return rf, lines, round((len(lines) - 1) * body["line_height"])


def draw_body(img: Image.Image, rf: RichFont, lines: list[str], body: dict) -> None:
    for i, line in enumerate(lines):
        rf.draw(img, body["left"], body["baseline"] + i * body["line_height"], line, hex_to_rgb(body["colour"]))


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_screenshot(cfg: dict, text: str, custom: dict[str, Image.Image]) -> bytes:
    """`text` as the body of a screenshot (e.g. an X post), stretched at `split_y` for each extra line"""
    rf, lines, extra_h = layout_body(cfg["body"], text, custom)
    img = stretched(TEMPLATE_DIR / cfg["background"], cfg["split_y"], extra_h, hex_to_rgb(cfg["fill"]))
    draw_body(img, rf, lines, cfg["body"])
    return to_png(img)


def render_discord(cfg: dict, text: str, custom: dict[str, Image.Image]) -> bytes:
    """`text` as a Discord message, with the avatar, name and timestamp drawn from config"""
    body = cfg["body"]
    rf, lines, extra_h = layout_body(body, text, custom)
    img = Image.new("RGB", (cfg["width"], cfg["height"] + extra_h), hex_to_rgb(cfg["background"]))

    avatar_cfg = cfg["avatar"]
    size = avatar_cfg["size"]
    avatar = ImageOps.fit(Image.open(TEMPLATE_DIR / avatar_cfg["image"]).convert("RGBA"), (size * SUPERSAMPLE,) * 2)
    mask = Image.new("L", avatar.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, *avatar.size), fill=255)
    avatar.putalpha(ImageChops.multiply(avatar.getchannel("A"), mask))
    avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
    img.paste(avatar, (avatar_cfg["x"], avatar_cfg["y"]), avatar)

    name, stamp = cfg["name"], cfg["timestamp"]
    name_font = rich_font(name["font"])
    name_font.draw(img, body["left"], cfg["header_baseline"], name["text"], hex_to_rgb(name["colour"]))
    stamp_x = body["left"] + name_font.width(name["text"]) + stamp["gap"]
    rich_font(stamp["font"]).draw(img, stamp_x, cfg["header_baseline"], stamp["text"], hex_to_rgb(stamp["colour"]))

    draw_body(img, rf, lines, body)
    return to_png(img)


def render_dialogue(cfg: dict, text: str, custom: dict[str, Image.Image]) -> bytes:
    """`text` in a visual-novel dialogue box, shrinking through `sizes` until it fits (then cut with an ellipsis)"""
    body = cfg["body"]
    img = Image.open(TEMPLATE_DIR / cfg["background"]).convert("RGB")
    left, top, right, bottom = cfg["box"]
    max_w, max_h = right - left, bottom - top

    for size in cfg["sizes"]:
        rf = rich_font(body["font"], body.get("emoji"), size, custom)
        line_h = round(size * cfg["line_gap"])
        max_lines = max_h // line_h
        lines = rf.wrap(text, max_w, max_lines + 1)
        if len(lines) <= max_lines:
            break
    else:
        lines = rf.wrap(text, max_w, max_lines)

    for i, line in enumerate(lines):
        rf.draw(img, left, top + i * line_h + rf.ascent, line, hex_to_rgb(body["colour"]), cfg.get("shadow", 0))
    return to_png(img)


RENDERERS = {"screenshot": render_screenshot, "discord": render_discord, "dialogue": render_dialogue}


def render(name: str, text: str, custom_emoji: dict[str, bytes] | None = None) -> bytes:
    """`text` drawn into the template `name`; `custom_emoji` maps emoji ids to images (codes without one show as :name:)"""
    custom_emoji = custom_emoji or {}
    stand_ins = {emoji_id: chr(CUSTOM_BASE + i) for i, emoji_id in enumerate(custom_emoji)}
    custom = {stand_ins[emoji_id]: Image.open(io.BytesIO(data)).convert("RGBA") for emoji_id, data in custom_emoji.items()}
    text = CUSTOM_EMOJI.sub(lambda match: stand_ins.get(match[2], f":{match[1]}:"), text)
    cfg = TEMPLATES[name]
    return RENDERERS[cfg["style"]](cfg, text, custom)
