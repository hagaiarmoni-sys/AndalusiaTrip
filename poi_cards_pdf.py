"""
poi_cards_pdf.py

NEW module: render POIs as "cards" in the PDF (photo + details), without changing the rest of the PDF.

Designed to be called from pdf_generator.py (or a patched copy) like:

    from poi_cards_pdf import render_poi_cards
    render_poi_cards(
        pdf=pdf,
        pois=attractions[:6],
        get_photo_path=get_photo_path,
        safe_text=safe_text,
        theme={"text": COLOR_TEXT, "light": COLOR_LIGHT, "accent": COLOR_ATTR, "primary": COLOR_PRIMARY},
        cards_per_page=3,
        max_cards=6,
    )

Fields shown (under each rounded-corner photo):
- Name
- Short description
- Avg time spent  (supports: avg_time_spent / average_time_spent / recommended_duration / duration / etc.)
- Rating
- # reviewers
- Tips (1–2 bullet tips)

If the POI does not contain a duration field, we still print:
    Avg time spent: —
so you can always see the line (template-style).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
import os
import re
import hashlib
import tempfile

try:
    from PIL import Image, ImageDraw
except Exception as _e:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


# ----------------------------
# Small helpers
# ----------------------------

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
    return s[: max(0, max_chars - 1)].rstrip() + "…"


def _format_rating(r: Any) -> Optional[str]:
    if r is None:
        return None
    try:
        rf = float(str(r).strip())
        # show 1 decimal if needed
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
    """
    Returns a compact duration string like:
      2h, 1.5h, 90min, 1-2h, ~2h, 2 hours
    """
    if v is None:
        return None

    # numeric -> hours
    if isinstance(v, (int, float)):
        if v <= 0:
            return None
        # treat <= 12 as hours
        if v <= 12:
            if abs(v - round(v)) < 1e-9:
                return f"{int(round(v))}h"
            return f"{v:.1f}h"
        # otherwise assume minutes
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

    # normalize common patterns
    s2 = s.lower()
    s2 = s2.replace("hours", "h").replace("hour", "h").replace("hrs", "h").replace("hr", "h")
    s2 = s2.replace("minutes", "min").replace("minute", "min").replace("mins", "min")
    s2 = re.sub(r"\s+", " ", s2).strip()
    # keep reasonably short
    if len(s2) > 16:
        s2 = s2[:16].rstrip() + "…"
    return s2


def _mm_to_px(mm: float, dpi: int = 150) -> int:
    return max(1, int(round(mm * dpi / 25.4)))


def _rounded_png_from_image(
    img_path: str,
    target_w_mm: float,
    target_h_mm: float,
    radius_mm: float = 3.0,
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
        # cover-crop to target aspect ratio
        src_w, src_h = im.size
        target_ratio = w_px / float(h_px)
        src_ratio = src_w / float(src_h)

        if src_ratio > target_ratio:
            # wider -> crop width
            new_w = int(round(src_h * target_ratio))
            left = max(0, (src_w - new_w) // 2)
            im = im.crop((left, 0, left + new_w, src_h))
        else:
            # taller -> crop height
            new_h = int(round(src_w / target_ratio))
            top = max(0, (src_h - new_h) // 2)
            im = im.crop((0, top, src_w, top + new_h))

        im = im.resize((w_px, h_px), Image.LANCZOS)

        # rounded mask
        mask = Image.new("L", (w_px, h_px), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, w_px - 1, h_px - 1), radius=r_px, fill=255)

        rounded = Image.new("RGBA", (w_px, h_px), (255, 255, 255, 0))
        rounded.paste(im, (0, 0), mask=mask)

        rounded.save(out_path, format="PNG")
        return out_path
    except Exception:
        return None


def _as_tip_list(tips: Any, max_items: int = 2) -> List[str]:
    if tips is None:
        return []
    if isinstance(tips, (list, tuple)):
        out = [str(t).strip() for t in tips if str(t).strip()]
    else:
        # split on newline / bullet / semicolon
        s = str(tips).strip()
        if not s:
            return []
        parts = re.split(r"[\n•;\u2022]+", s)
        out = [p.strip(" -\t").strip() for p in parts if p.strip(" -\t").strip()]
    return out[:max_items]


# ---------------------------------------------------------------------------
# Placeholder / template tips (ONLY used when show_placeholders=True)
# ---------------------------------------------------------------------------

_DEFAULT_PLACEHOLDER_TIPS: List[str] = [
    "Go early/late for fewer crowds and better photos",
    "Charge your phone — you’ll take lots of photos",
]

_PLACEHOLDER_TIP_PATTERNS = [
    re.compile(r"\bplaceholder\b", re.I),
    re.compile(r"tip\s*#\s*\d+\s*placeholder", re.I),
    re.compile(r"go\s*early\s*/?\s*late\s*for\s*fewer\s*crowds\s*and\s*better\s*photos", re.I),
]

def _looks_like_placeholder_tip(t: str) -> bool:
    s = (t or "").strip()
    if not s:
        return True
    for pat in _PLACEHOLDER_TIP_PATTERNS:
        if pat.search(s):
            return True
    return False


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
        poi.get("time_spent"),
        poi.get("time_needed"),
        poi.get("typical_duration"),
    )
    return _format_avg_time(raw)


# ----------------------------
# Main renderer
# ----------------------------

def render_poi_cards(
    pdf: Any,
    pois: Sequence[Dict[str, Any]],
    get_photo_path: Callable[[Dict[str, Any]], Optional[str]],
    safe_text: Callable[..., str],
    theme: Optional[Dict[str, Tuple[int, int, int]]] = None,
    cards_per_page: int = 3,
    max_cards: int = 6,
    # If True, fill missing fields with placeholders (useful for design mockups only)
    show_placeholders: bool = False,
    # If True (default), automatically remove common placeholder tips from the final PDF
    drop_placeholder_tips: bool = True,
) -> None:
    """
    Draw POI cards starting at the current cursor position (pdf.get_y()).
    Adds pages automatically if needed.

    IMPORTANT: This function only draws; it does not add section titles.
    """
    if not pois:
        return

    # Theme defaults (match pdf_generator palette if provided)
    theme = theme or {}
    c_text = theme.get("text", (52, 73, 94))
    c_light = theme.get("light", (127, 140, 141))
    c_accent = theme.get("accent", (155, 89, 182))
    c_primary = theme.get("primary", (41, 128, 185))

    # Geometry
    page_w = float(getattr(pdf, "w", 210))
    page_h = float(getattr(pdf, "h", 297))
    l_margin = float(getattr(pdf, "l_margin", 15))
    r_margin = float(getattr(pdf, "r_margin", 15))
    b_margin = float(getattr(pdf, "b_margin", 15))

    x0 = l_margin
    usable_w = page_w - l_margin - r_margin
    gap_y = 6.0

    # Card sizing:
    # Use "cards_per_page" as *vertical* density guidance.
    # We keep cards full-width and compute a comfortable height.
    top_pad = 4.0
    side_pad = 4.0
    photo_h = 32.0  # mm
    # text area roughly ~40mm, plus padding
    base_card_h = photo_h + 40.0
    # If user requests tighter density, shrink a bit
    if cards_per_page >= 4:
        base_card_h = photo_h + 34.0

    card_w = usable_w
    card_h = base_card_h

    # Soft border
    def _draw_card_border(x: float, y: float, w: float, h: float) -> None:
        pdf.set_draw_color(220, 225, 230)
        pdf.set_line_width(0.4)
        pdf.rect(x, y, w, h)

    def _multi_cell_at(x: float, y: float, w: float, h: float, txt: str) -> float:
        pdf.set_xy(x, y)
        pdf.multi_cell(w, h, txt)
        return float(pdf.get_y())

    def _ensure_space(need_h: float) -> None:
        y = float(pdf.get_y())
        if y + need_h > page_h - b_margin:
            pdf.add_page()

    shown = 0
    for poi in list(pois)[: max_cards]:
        _ensure_space(card_h + gap_y)
        x = x0
        y = float(pdf.get_y())

        # Card border
        _draw_card_border(x, y, card_w, card_h)

        # Photo (rounded corners)
        photo_path = None
        try:
            photo_path = get_photo_path(poi)
        except Exception:
            photo_path = None

        img_x = x + side_pad
        img_y = y + top_pad
        img_w = card_w - 2 * side_pad
        img_h = photo_h

        if photo_path and os.path.exists(photo_path):
            rounded = _rounded_png_from_image(photo_path, img_w, img_h, radius_mm=3.5)
            try:
                pdf.image(rounded or photo_path, x=img_x, y=img_y, w=img_w, h=img_h)
            except Exception:
                pass
        else:
            # Placeholder image box
            pdf.set_draw_color(235, 235, 235)
            pdf.set_line_width(0.4)
            pdf.rect(img_x, img_y, img_w, img_h)

        # Text block starts under photo
        tx = x + side_pad
        ty = img_y + img_h + 3.5
        tw = card_w - 2 * side_pad

        name = safe_text(poi.get("name", "Attraction"), 55)

        desc_raw = _first_nonempty(poi.get("description"), poi.get("short_description"), poi.get("details"))
        desc = safe_text(_compact(str(desc_raw) if desc_raw is not None else "", 170), 220)

        avg_time = _extract_avg_time(poi)  # <-- THIS IS THE LINE YOU WERE MISSING
        rating = _format_rating(_first_nonempty(poi.get("rating"), poi.get("google_rating")))
        reviewers = _format_reviews(
            _first_nonempty(
                poi.get("reviews_count"),
                poi.get("review_count"),
                poi.get("user_ratings_total"),
                poi.get("reviewers"),
                poi.get("num_reviews"),
            )
        )

        tips = _as_tip_list(_first_nonempty(poi.get("tips"), poi.get("tip"), poi.get("local_tip"), poi.get("pro_tip")))

        # Final PDFs should NOT contain fake/generic tips.
        # So by default we remove placeholder-looking tips.
        if drop_placeholder_tips and not show_placeholders:
            tips = [t for t in tips if not _looks_like_placeholder_tip(t)]

        # For design mockups only: if there are no tips, show nice placeholders
        if show_placeholders and not tips:
            tips = _DEFAULT_PLACEHOLDER_TIPS[:2]

        # Name
        pdf.set_text_color(*c_text)
        pdf.set_font("Helvetica", "B", 12)
        ty = _multi_cell_at(tx, ty, tw, 6, name) + 0.5

        # Description
        if desc:
            pdf.set_text_color(*c_light)
            pdf.set_font("Helvetica", "", 9)
            ty = _multi_cell_at(tx, ty, tw, 4.6, desc) + 0.8

        # Meta lines (ALWAYS show Avg time spent)
        pdf.set_text_color(*c_text)
        pdf.set_font("Helvetica", "", 9)
        avg_line = f"Avg time spent: {avg_time if avg_time else '—'}"
        ty = _multi_cell_at(tx, ty, tw, 4.8, safe_text(avg_line, 60)) + 0.2

        meta_parts = []
        if rating:
            meta_parts.append(f"Rating: {rating}")
        if reviewers:
            meta_parts.append(f"Reviews: {reviewers}")
        if meta_parts:
            pdf.set_text_color(*c_primary)
            pdf.set_font("Helvetica", "I", 9)
            ty = _multi_cell_at(tx, ty, tw, 4.8, safe_text(" | ".join(meta_parts), 80)) + 0.6

        # Tips
        if tips:
            pdf.set_text_color(*c_accent)
            pdf.set_font("Helvetica", "B", 9)
            ty = _multi_cell_at(tx, ty, tw, 4.8, "Tips") + 0.2

            pdf.set_text_color(*c_text)
            pdf.set_font("Helvetica", "", 9)
            for t in tips:
                ty = _multi_cell_at(tx + 2.0, ty, tw - 2.0, 4.6, safe_text(f"• {t}", 90)) + 0.1

        # Move cursor to next card
        pdf.set_xy(x0, y + card_h + gap_y)

        shown += 1

    # small spacing after cards
    pdf.ln(1)
