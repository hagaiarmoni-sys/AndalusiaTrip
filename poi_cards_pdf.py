"""
POI card rendering for the Andalusia Travel App PDF.

Goal:
- Keep the existing PDF exactly the same, except for HOW POIs ("Today's Highlights") are rendered.
- Render POIs as compact "cards" with a (rounded-corners) photo and key fields.

Usage (inside pdf_generator.py):
    from poi_cards_pdf import render_poi_cards
    render_poi_cards(pdf, attractions[:6], get_photo_path, safe_text, theme={...}, cards_per_page=3)

Notes:
- Rounded corners are achieved by preprocessing each image into a PNG with transparent rounded corners (Pillow).
- If Pillow isn't available, it falls back to non-rounded images.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import os
import tempfile
import hashlib

try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


# Cache processed images so we don't re-generate the same rounded PNG many times
_ROUNDED_CACHE: Dict[Tuple[str, int, int, int], str] = {}


def _mm_to_px(mm: float, dpi: int = 160) -> int:
    # 25.4 mm = 1 inch
    return max(1, int(mm * dpi / 25.4))


def _rounded_image_to_temp(
    photo_path: str,
    w_mm: float,
    h_mm: float,
    radius_mm: float = 3.5,
) -> Optional[str]:
    """Return a temp PNG path with rounded corners (transparent outside radius)."""
    if not photo_path or not os.path.exists(photo_path):
        return None
    if Image is None:
        # Fallback: no rounding, return original
        return photo_path

    key = (photo_path, int(w_mm * 10), int(h_mm * 10), int(radius_mm * 10))
    cached = _ROUNDED_CACHE.get(key)
    if cached and os.path.exists(cached):
        return cached

    try:
        img = Image.open(photo_path).convert("RGBA")

        target_w = _mm_to_px(w_mm)
        target_h = _mm_to_px(h_mm)

        # Center-crop to the target aspect ratio ("cover" behavior)
        src_w, src_h = img.size
        src_ratio = src_w / max(1, src_h)
        tgt_ratio = target_w / max(1, target_h)

        if src_ratio > tgt_ratio:
            # Too wide -> crop left/right
            new_w = int(src_h * tgt_ratio)
            left = max(0, (src_w - new_w) // 2)
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            # Too tall -> crop top/bottom
            new_h = int(src_w / tgt_ratio)
            top = max(0, (src_h - new_h) // 2)
            img = img.crop((0, top, src_w, top + new_h))

        img = img.resize((target_w, target_h))

        radius_px = _mm_to_px(radius_mm)

        mask = Image.new("L", (target_w, target_h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, target_w, target_h), radius=radius_px, fill=255)

        out = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 0))
        out.paste(img, (0, 0), mask)

        # Stable temp filename for caching
        h = hashlib.md5(f"{photo_path}|{key}".encode("utf-8")).hexdigest()[:12]
        tmp_path = os.path.join(tempfile.gettempdir(), f"poi_round_{h}.png")
        out.save(tmp_path, format="PNG")

        _ROUNDED_CACHE[key] = tmp_path
        return tmp_path

    except Exception:
        # If anything goes wrong, fallback to original image
        return photo_path


def _first_nonempty(*vals: Any) -> str:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list) and v:
            for x in v:
                if isinstance(x, str) and x.strip():
                    return x.strip()
            return str(v[0])
    return ""


def _format_avg_time(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        # assume hours
        if isinstance(raw, float) and raw.is_integer():
            return f"{int(raw)}h"
        if isinstance(raw, int):
            return f"{raw}h"
        return f"{raw:.1f}h"
    s = str(raw).strip()
    s = s.replace("hours", "h").replace("hour", "h")
    s = s.replace("minutes", "min").replace("minute", "min")
    return s


def _compact(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def render_poi_cards(
    pdf: Any,
    pois: List[Dict[str, Any]],
    get_photo_path: Callable[[Dict[str, Any]], Optional[str]],
    safe_text: Callable[[Any, int], str],
    theme: Optional[Dict[str, Tuple[int, int, int]]] = None,
    cards_per_page: int = 3,
    max_cards: int = 6,
) -> None:
    """
    Render POIs as booking-style cards.

    Fields shown under each photo:
      - Name
      - Short description
      - Average time spent
      - Rating
      - # of reviewers
      - Tip
    """
    theme = theme or {}
    c_text = theme.get("text", (52, 73, 94))
    c_light = theme.get("light", (127, 140, 141))
    c_accent = theme.get("accent", (155, 89, 182))

    # Geometry (mm)
    x0 = float(getattr(pdf, "l_margin", 15))
    w = float(getattr(pdf, "w", 210)) - float(getattr(pdf, "l_margin", 15)) - float(getattr(pdf, "r_margin", 15))
    pad = 3.0
    gap = 6.0

    card_h = 62.0
    img_h = 26.0
    radius_mm = 3.5

    per_page = 0

    for idx, poi in enumerate(pois[:max_cards], 1):
        # enforce 3 cards per page (best-effort) within the highlight section
        if per_page >= cards_per_page:
            pdf.add_page()
            per_page = 0

        # If not enough room for the next card, go to next page
        if float(pdf.get_y()) + card_h > float(getattr(pdf, "h", 297)) - float(getattr(pdf, "b_margin", 15)):
            pdf.add_page()
            per_page = 0

        y0 = float(pdf.get_y())

        # Card background
        try:
            pdf.set_draw_color(220, 220, 220)
            pdf.set_fill_color(250, 250, 250)
            pdf.rect(x0, y0, w, card_h, style="DF")
        except Exception:
            pass

        # Image (rounded)
        img_x = x0 + pad
        img_y = y0 + pad
        img_w = w - 2 * pad

        photo_path = None
        try:
            photo_path = get_photo_path(poi)
        except Exception:
            photo_path = None

        if photo_path:
            rounded_path = _rounded_image_to_temp(photo_path, img_w, img_h, radius_mm=radius_mm)
            if rounded_path and os.path.exists(rounded_path):
                try:
                    pdf.image(rounded_path, x=img_x, y=img_y, w=img_w, h=img_h)
                except Exception:
                    pass
        else:
            # Placeholder image area
            try:
                pdf.set_fill_color(240, 240, 240)
                pdf.rect(img_x, img_y, img_w, img_h, style="F")
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(150, 150, 150)
                pdf.set_xy(img_x, img_y + img_h / 2 - 3)
                pdf.cell(img_w, 6, "Photo", align="C")
            except Exception:
                pass

        # Text block under photo
        t_x = x0 + pad
        t_y = img_y + img_h + 2.0
        try:
            pdf.set_xy(t_x, t_y)
        except Exception:
            pass

        name = safe_text(poi.get("name", "Attraction"), 55)

        desc = _first_nonempty(poi.get("description"), poi.get("details"), poi.get("short_description"))
        desc = safe_text(_compact(desc, 170), 200)

        avg_time = _format_avg_time(_first_nonempty(poi.get("average_time_spent"), poi.get("avg_time_spent"), poi.get("recommended_duration"), poi.get("duration")))
        rating = _first_nonempty(poi.get("rating"), poi.get("google_rating"))
        reviewers = _first_nonempty(
            poi.get("reviews_count"),
            poi.get("review_count"),
            poi.get("user_ratings_total"),
            poi.get("reviewers"),
            poi.get("num_reviews"),
            poi.get("reviews"),
        )

        tip = _first_nonempty(poi.get("tip"), poi.get("tips"), poi.get("local_tip"), poi.get("pro_tip"))
        if not tip:
            tip = "Tip: Go early/late for fewer crowds and better photos."
        tip = safe_text(_compact(tip, 140), 160)

        # Title
        try:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*c_text)
            pdf.multi_cell(w - 2 * pad, 5, f"{idx}. {name}")
        except Exception:
            pass

        # Description
        try:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*c_text)
            pdf.set_x(t_x)
            pdf.multi_cell(w - 2 * pad, 4, desc)
        except Exception:
            pass

        # Info line
        info_parts = []
        if avg_time:
            info_parts.append(f"Avg time: {avg_time}")
        if rating:
            info_parts.append(f"Rating: {rating}")
        if reviewers:
            info_parts.append(f"Reviews: {reviewers}")

        if info_parts:
            try:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(*c_light)
                pdf.set_x(t_x)
                pdf.multi_cell(w - 2 * pad, 4, " | ".join(info_parts))
            except Exception:
                pass

        # Tip line
        try:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*c_accent)
            pdf.set_x(t_x)
            pdf.multi_cell(w - 2 * pad, 4, tip)
        except Exception:
            pass

        # Advance cursor to just after the card
        try:
            pdf.set_y(y0 + card_h + gap)
        except Exception:
            pass

        per_page += 1
