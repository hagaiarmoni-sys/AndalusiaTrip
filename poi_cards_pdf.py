"""
poi_cards_pdf.py

NEW module: render POIs as Booking-style "cards" inside the existing PDF (FPDF),
with rounded-corner photos and a compact meta row (rating badge + avg time + reviews).

✅ IMPORTANT:
- This module does NOT change the rest of the PDF.
- It only draws the POI cards where you call render_poi_cards().
- Tips are shown ONLY if the POI already contains real tips in its data.
- Avg time: if missing in the POI data, we can (optionally) show an ESTIMATE based on category/types.

Supported avg-time keys (first non-empty wins):
- avg_time_spent / average_time_spent / avg_time / average_time
- recommended_duration / recommended_visit_duration / visit_duration / duration
- visit_duration_hours / recommended_duration_hours / visit_duration_minutes / duration_minutes / typical_duration

Supported rating keys:
- rating / google_rating

Supported reviews keys:
- reviews_count / review_count / user_ratings_total / reviewers / num_reviews / reviews

Supported tips keys:
- tips (list or string), tip, local_tip, pro_tip
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import os
import re
import hashlib
import tempfile

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


# ----------------------------
# helpers
# ----------------------------

_PLACEHOLDER_TIP_RE = re.compile(r"(go early|go late|fewer crowds|better photos)", re.I)

def _first_nonempty(*vals: Any) -> Any:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, (list, tuple, dict)) and len(v) == 0:
            continue
        return v
    return None


def _compact(s: str, max_chars: int) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 1)].rstrip() + "..."


def _format_rating(r: Any) -> Optional[str]:
    if r is None:
        return None
    try:
        rf = float(str(r).strip())
        if abs(rf - round(rf)) < 1e-9:
            return f"{int(round(rf))}"
        return f"{rf:.1f}"
    except Exception:
        s = str(r).strip()
        return s if s else None


def _format_reviews(n: Any) -> Optional[str]:
    if n is None:
        return None
    try:
        nf = int(float(str(n).replace(",", "").strip()))
        if nf < 0:
            return None
        return f"{nf:,}"
    except Exception:
        s = str(n).strip()
        return s if s else None


def _format_avg_time(v: Any) -> Optional[str]:
    # numeric -> hours
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if v <= 0:
            return None
        # treat <=12 as hours
        if v <= 12:
            if abs(v - round(v)) < 1e-9:
                return f"{int(round(v))}h"
            return f"{v:.1f}h"
        # otherwise minutes
        return f"{int(round(v))}min"

    s = str(v).strip()
    if not s:
        return None

    # "2" -> 2h
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            f = float(s)
            if f <= 12:
                if abs(f - round(f)) < 1e-9:
                    return f"{int(round(f))}h"
                return f"{f:.1f}h"
        except Exception:
            pass

    s2 = s.lower()
    s2 = s2.replace("hours", "h").replace("hour", "h").replace("hrs", "h").replace("hr", "h")
    s2 = s2.replace("minutes", "min").replace("minute", "min").replace("mins", "min")
    s2 = re.sub(r"\s+", " ", s2).strip()
    if len(s2) > 16:
        s2 = s2[:16].rstrip() + "..."
    return s2


def _extract_avg_time(poi: Dict[str, Any]) -> Optional[str]:
    raw = _first_nonempty(
        poi.get("avg_time_spent"),
        poi.get("average_time_spent"),
        poi.get("avg_time"),
        poi.get("average_time"),
        poi.get("recommended_duration"),
        poi.get("recommended_visit_duration"),
        poi.get("visit_duration"),
        poi.get("duration"),
        poi.get("visit_duration_hours"),
        poi.get("recommended_duration_hours"),
        poi.get("visit_duration_minutes"),
        poi.get("duration_minutes"),
        poi.get("typical_duration"),
    )
    return _format_avg_time(raw)


def _estimate_avg_time(poi: Dict[str, Any]) -> Optional[str]:
    """
    Conservative estimate when no duration exists in the POI data.
    Returns e.g. "2h" (we will display it as "Avg time: 2h (est.)").
    """
    name = (poi.get("name") or "").lower()
    cat = (poi.get("category") or "").lower()
    sub = (poi.get("subcategory") or "").lower()
    types = poi.get("google_types") or []
    if isinstance(types, str):
        types = [t.strip() for t in types.split(",") if t.strip()]
    types_set = set([str(t).lower() for t in (types or [])])

    text = f"{name} {cat} {sub}"

    # very short stops
    if any(k in text for k in ["mirador", "viewpoint", "lookout", "plaza", "square"]):
        return "0.5h"

    # hiking / trails
    if any(k in text for k in ["caminito", "trail", "hike", "sendero", "ruta", "gorge"]):
        return "3h"

    # museums
    if "museum" in text or "museo" in text or "museum" in types_set:
        return "1.5h"

    # fortresses / castles / palaces / cathedrals
    if any(k in text for k in ["alcazaba", "castle", "castillo", "fort", "fortress", "palacio", "palace", "cathedral", "catedral", "mezquita", "monastery", "monasterio"]):
        return "2h"

    # parks / gardens
    if any(k in text for k in ["park", "parque", "garden", "jardin", "jardín"]):
        return "1h"

    # beaches
    if any(k in text for k in ["beach", "playa"]):
        return "2h"

    # default if it's a tourist attraction but unknown
    if "tourist_attraction" in types_set:
        return "1.5h"

    return None


def _as_tip_list(tips: Any, max_items: int = 2) -> List[str]:
    if tips is None:
        return []
    if isinstance(tips, (list, tuple)):
        out = [str(t).strip() for t in tips if str(t).strip()]
    else:
        s = str(tips).strip()
        if not s:
            return []
        parts = re.split(r"[\n•;\u2022]+", s)
        out = [p.strip(" -\t").strip() for p in parts if p.strip(" -\t").strip()]

    # remove placeholder-ish tips
    cleaned: List[str] = []
    for t in out:
        if _PLACEHOLDER_TIP_RE.search(t):
            continue
        cleaned.append(t)
    return cleaned[:max_items]


def _mm_to_px(mm: float, dpi: int = 150) -> int:
    return max(1, int(round(mm * dpi / 25.4)))


def _rounded_png_from_image(
    img_path: str,
    target_w_mm: float,
    target_h_mm: float,
    radius_mm: float = 4.0,
    dpi: int = 150,
) -> Optional[str]:
    """
    Create (and cache) a rounded-corners PNG version of the image sized to the target.
    Returns the path to the PNG, or None if Pillow isn't available or image can't be processed.
    """
    if Image is None:
        return None
    if not img_path or not os.path.exists(img_path):
        return None

    cache_dir = os.path.join(tempfile.gettempdir(), "otravel_poi_card_cache")
    os.makedirs(cache_dir, exist_ok=True)

    key = f"{img_path}|{target_w_mm:.2f}|{target_h_mm:.2f}|{radius_mm:.2f}|{dpi}"
    fn = hashlib.md5(key.encode("utf-8")).hexdigest() + ".png"
    out_path = os.path.join(cache_dir, fn)
    if os.path.exists(out_path):
        return out_path

    try:
        w_px = _mm_to_px(target_w_mm, dpi)
        h_px = _mm_to_px(target_h_mm, dpi)
        r_px = _mm_to_px(radius_mm, dpi)

        im = Image.open(img_path).convert("RGBA")
        src_w, src_h = im.size
        target_ratio = w_px / float(h_px)
        src_ratio = src_w / float(src_h)

        # cover-crop to target aspect ratio
        if src_ratio > target_ratio:
            new_w = int(round(src_h * target_ratio))
            left = max(0, (src_w - new_w) // 2)
            im = im.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(round(src_w / target_ratio))
            top = max(0, (src_h - new_h) // 2)
            im = im.crop((0, top, src_w, top + new_h))

        im = im.resize((w_px, h_px), Image.LANCZOS)

        mask = Image.new("L", (w_px, h_px), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, w_px - 1, h_px - 1), radius=r_px, fill=255)

        rounded = Image.new("RGBA", (w_px, h_px), (255, 255, 255, 0))
        rounded.paste(im, (0, 0), mask=mask)
        rounded.save(out_path, format="PNG")
        return out_path
    except Exception:
        return None


def _wrap_lines(pdf: Any, text: str, max_w: float, font_name: str, font_style: str, font_size: int) -> List[str]:
    """
    Very small wrapper: returns line list based on pdf.get_string_width.
    """
    pdf.set_font(font_name, font_style, font_size)
    words = (text or "").split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if pdf.get_string_width(test) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _rounded_rect(pdf: Any, x: float, y: float, w: float, h: float, r: float, style: str = "D") -> None:
    """
    Use rounded_rect if available (fpdf2). Otherwise fallback to rect.
    style: "D" draw, "F" fill, "DF" both
    """
    if hasattr(pdf, "rounded_rect"):
        pdf.rounded_rect(x, y, w, h, r, style=style)
    else:
        # fallback: plain rect
        if "F" in style:
            pdf.rect(x, y, w, h, style="F")
        else:
            pdf.rect(x, y, w, h)


# ----------------------------
# public API
# ----------------------------

def render_poi_cards(
    pdf: Any,
    pois: Sequence[Dict[str, Any]],
    get_photo_path: Callable[[Dict[str, Any]], Optional[str]],
    safe_text: Callable[..., str],
    theme: Optional[Dict[str, Tuple[int, int, int]]] = None,
    cards_per_page: int = 4,
    max_cards: int = 6,
    estimate_missing_time: bool = True,
) -> None:
    """
    Booking-style grid cards: 2 columns, 2 rows per page (4 per page).
    If max_cards=6 -> page1: 4 cards, page2: 2 cards.

    NOTE: cards_per_page is kept for backward compatibility with your existing call,
    but this renderer is optimized for the 2x2 grid look (like your screenshot).
    """
    if not pois:
        return

    theme = theme or {}
    c_text = theme.get("text", (52, 73, 94))
    c_muted = theme.get("light", (127, 140, 141))
    c_accent = theme.get("accent", (155, 89, 182))
    c_primary = theme.get("primary", (41, 128, 185))

    page_w = float(getattr(pdf, "w", 210))
    page_h = float(getattr(pdf, "h", 297))
    l_margin = float(getattr(pdf, "l_margin", 15))
    r_margin = float(getattr(pdf, "r_margin", 15))
    b_margin = float(getattr(pdf, "b_margin", 15))

    x0 = l_margin
    usable_w = page_w - l_margin - r_margin

    cols = 2
    gap_x = 6.0
    gap_y = 8.0

    card_w = (usable_w - gap_x) / cols
    # height tuned to match your "enclosed" template
    card_h = 108.0
    pad = 4.0

    # Photo area
    photo_h = 48.0
    radius = 5.0  # card rounding for border (if supported)
    photo_radius = 5.0

    def ensure_row_space(row_h: float) -> None:
        y = float(pdf.get_y())
        if y + row_h > page_h - b_margin:
            pdf.add_page()

    def draw_card(poi: Dict[str, Any], x: float, y: float) -> None:
        # shadow
        pdf.set_fill_color(245, 247, 249)
        pdf.rect(x + 1.2, y + 1.2, card_w, card_h, style="F")

        # border
        pdf.set_draw_color(225, 231, 236)
        pdf.set_line_width(0.4)
        pdf.set_fill_color(255, 255, 255)
        _rounded_rect(pdf, x, y, card_w, card_h, radius, style="DF")

        # photo (rounded)
        photo_x = x + pad
        photo_y = y + pad
        photo_w = card_w - 2 * pad

        photo_path = None
        try:
            photo_path = get_photo_path(poi)
        except Exception:
            photo_path = None

        if photo_path and os.path.exists(photo_path):
            rounded = _rounded_png_from_image(photo_path, photo_w, photo_h, radius_mm=photo_radius)
            try:
                pdf.image(rounded or photo_path, x=photo_x, y=photo_y, w=photo_w, h=photo_h)
            except Exception:
                pass
        else:
            # placeholder
            pdf.set_draw_color(235, 235, 235)
            pdf.rect(photo_x, photo_y, photo_w, photo_h)

        # content start
        cx = x + pad
        cy = photo_y + photo_h + 4.0
        content_w = card_w - 2 * pad

        name = safe_text(poi.get("name", "Attraction"), 60)
        desc_raw = _first_nonempty(poi.get("description"), poi.get("short_description"), poi.get("details"))
        desc = safe_text(_compact(str(desc_raw) if desc_raw is not None else "", 190), 220)

        avg_time = _extract_avg_time(poi)
        est = False
        if not avg_time and estimate_missing_time:
            avg_time = _estimate_avg_time(poi)
            est = bool(avg_time)

        rating = _format_rating(_first_nonempty(poi.get("rating"), poi.get("google_rating")))
        reviews = _format_reviews(_first_nonempty(poi.get("reviews_count"), poi.get("review_count"), poi.get("user_ratings_total"), poi.get("reviewers"), poi.get("num_reviews"), poi.get("reviews")))

        tips = _as_tip_list(_first_nonempty(poi.get("tips"), poi.get("tip"), poi.get("local_tip"), poi.get("pro_tip")))

        # Title (max 2 lines)
        pdf.set_text_color(*c_text)
        title_lines = _wrap_lines(pdf, name, content_w, "Helvetica", "B", 12)[:2]
        pdf.set_font("Helvetica", "B", 12)
        for ln in title_lines:
            pdf.set_xy(cx, cy)
            pdf.cell(content_w, 6, ln, ln=1)
            cy += 6.0

        # Desc (max 3 lines)
        if desc:
            pdf.set_text_color(*c_muted)
            desc_lines = _wrap_lines(pdf, desc, content_w, "Helvetica", "", 9)[:3]
            pdf.set_font("Helvetica", "", 9)
            for ln in desc_lines:
                pdf.set_xy(cx, cy)
                pdf.cell(content_w, 4.6, ln, ln=1)
                cy += 4.6
            cy += 2.0

        # Meta row: rating badge + avg time + reviews
        # badge
        badge_w, badge_h = 16.0, 10.0
        if rating:
            pdf.set_fill_color(15, 42, 67)  # dark navy
            pdf.set_draw_color(15, 42, 67)
            if hasattr(pdf, "rounded_rect"):
                pdf.rounded_rect(cx, cy, badge_w, badge_h, 2.0, style="F")
            else:
                pdf.rect(cx, cy, badge_w, badge_h, style="F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_xy(cx, cy + 2.0)
            pdf.cell(badge_w, 6, rating, align="C")
        else:
            # empty badge placeholder (keeps alignment)
            pdf.set_draw_color(230, 235, 239)
            pdf.rect(cx, cy, badge_w, badge_h)

        meta_x = cx + badge_w + 6.0
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*c_text)

        avg_label = "Avg time:"
        avg_val = avg_time if avg_time else "—"
        if est and avg_time:
            avg_val = f"{avg_time} (est.)"

        pdf.set_xy(meta_x, cy + 1.0)
        pdf.cell(content_w - (badge_w + 6.0), 5, f"{avg_label} {avg_val}", ln=1)

        pdf.set_text_color(*c_muted)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(meta_x, cy + 6.0)
        pdf.cell(content_w - (badge_w + 6.0), 5, f"{reviews} reviews" if reviews else "", ln=1)

        cy += 14.0

        # Tips (ONLY if real tips exist)
        if tips:
            pdf.set_text_color(*c_text)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_xy(cx, cy)
            pdf.cell(content_w, 6, "Tips", ln=1)
            cy += 6.0

            pdf.set_font("Helvetica", "", 9)
            for t in tips[:2]:
                pdf.set_text_color(10, 166, 166)  # teal bullet
                pdf.set_xy(cx, cy + 1.0)
                pdf.cell(4, 4, u"\u2022")
                pdf.set_text_color(*c_text)
                # wrap tip to max 2 lines
                t_lines = _wrap_lines(pdf, safe_text(t, 120), content_w - 6, "Helvetica", "", 9)[:2]
                pdf.set_xy(cx + 6, cy)
                pdf.multi_cell(content_w - 6, 4.6, "\n".join(t_lines))
                cy = float(pdf.get_y()) + 1.0

    # Render in rows of 2
    count = 0
    pois_to_draw = list(pois)[:max_cards]

    i = 0
    while i < len(pois_to_draw):
        ensure_row_space(card_h + gap_y)
        row_y = float(pdf.get_y())

        # first col
        draw_card(pois_to_draw[i], x0, row_y)
        i += 1

        # second col if exists
        if i < len(pois_to_draw):
            draw_card(pois_to_draw[i], x0 + card_w + gap_x, row_y)
            i += 1

        # move cursor to next row
        pdf.set_xy(x0, row_y + card_h + gap_y)

    # small spacing after section
    pdf.ln(1)
