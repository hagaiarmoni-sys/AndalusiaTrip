"""
POI card rendering for the Andalusia Travel App PDF.

Goal:
- Keep the existing PDF exactly the same, except for HOW POIs ("Today's Highlights") are rendered.
- Render POIs as booking-style cards in a 2x2 grid per page, with rounded-corner photos.

How to use (inside pdf_generator.py, replacing the old per-POI loop):
    from poi_cards_pdf import render_poi_cards

    render_poi_cards(
        pdf,
        attractions[:6],                # keep same count as before
        get_photo_path=get_photo_path,  # from pdf_generator.py
        safe_text=safe_text,            # from pdf_generator.py
    )

Notes:
- Rounded corners are achieved by preprocessing each image into a PNG with transparent rounded corners (Pillow).
- If Pillow isn't available, it falls back to non-rounded images.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import os
import tempfile
import hashlib
import re

try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


# ----------------------------
# Helpers
# ----------------------------

def _mm_to_px(mm: float, dpi: int = 160) -> int:
    # 25.4 mm = 1 inch
    return max(1, int(mm * dpi / 25.4))


def _center_crop_to_ratio(img: Any, target_w: int, target_h: int) -> Any:
    """Center-crop image to target aspect ratio, then resize to exact target size."""
    if img is None:
        return img
    iw, ih = img.size
    if iw <= 0 or ih <= 0:
        return img

    target_ratio = target_w / target_h
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        # crop width
        new_w = int(ih * target_ratio)
        left = max(0, (iw - new_w) // 2)
        box = (left, 0, left + new_w, ih)
    else:
        # crop height
        new_h = int(iw / target_ratio)
        top = max(0, (ih - new_h) // 2)
        box = (0, top, iw, top + new_h)

    img = img.crop(box)
    return img.resize((target_w, target_h), Image.LANCZOS)


def _rounded_image_to_temp(
    photo_path: str,
    w_mm: float,
    h_mm: float,
    radius_mm: float = 6.0,
) -> Optional[str]:
    """Return a temp PNG path with rounded corners (transparent outside radius)."""
    if not photo_path or not os.path.exists(photo_path):
        return None

    # Fallback: no rounding if PIL missing
    if Image is None or ImageDraw is None:
        return photo_path

    key = f"{photo_path}|{w_mm:.2f}|{h_mm:.2f}|{radius_mm:.2f}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()  # noqa: S324
    out_path = os.path.join(tempfile.gettempdir(), f"poi_round_{digest}.png")
    if os.path.exists(out_path):
        return out_path

    try:
        img = Image.open(photo_path).convert("RGB")
        w_px = _mm_to_px(w_mm)
        h_px = _mm_to_px(h_mm)

        img = _center_crop_to_ratio(img, w_px, h_px).convert("RGBA")

        # Rounded mask
        r_px = max(2, _mm_to_px(radius_mm))
        mask = Image.new("L", (w_px, h_px), 0)
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle((0, 0, w_px, h_px), radius=r_px, fill=255)

        out = Image.new("RGBA", (w_px, h_px), (255, 255, 255, 0))
        out.paste(img, (0, 0), mask)
        out.save(out_path, format="PNG")
        return out_path
    except Exception:
        return photo_path


def _wrap_lines(pdf: Any, text: str, max_w: float, max_lines: int) -> List[str]:
    """Greedy wrap by words using current font set on pdf. Returns <= max_lines."""
    words = (text or "").strip().split()
    if not words:
        return []
    lines: List[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if pdf.get_string_width(candidate) <= max_w or not cur:
            cur = candidate
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if len(lines) < max_lines and cur:
        lines.append(cur)

    # add ellipsis if truncated
    if len(lines) == max_lines and " ".join(words) != " ".join(lines).strip():
        last = lines[-1]
        while last and pdf.get_string_width(last + "…") > max_w:
            last = last[:-1]
        lines[-1] = (last.rstrip() + "…") if last else "…"
    return lines


def _pick_review_count(poi: Dict[str, Any]) -> Optional[int]:
    for k in ("reviewers", "reviews", "review_count", "user_ratings_total", "num_reviews"):
        v = poi.get(k)
        if v is None:
            continue
        try:
            if isinstance(v, str):
                v2 = int(re.sub(r"[^\d]", "", v))
            else:
                v2 = int(v)
            return v2 if v2 > 0 else None
        except Exception:
            continue
    return None


def _pick_rating(poi: Dict[str, Any]) -> Optional[float]:
    for k in ("rating", "google_rating", "avg_rating", "score"):
        v = poi.get(k)
        if v is None:
            continue
        try:
            r = float(str(v).strip())
            return r if r > 0 else None
        except Exception:
            continue
    return None


def _format_avg_time(raw: Any) -> str:
    """Return a compact string like '1.5h' or '90min' or '' if unknown."""
    if raw is None:
        return ""

    # numeric
    if isinstance(raw, (int, float)):
        try:
            f = float(raw)
        except Exception:
            return ""
        if f <= 0:
            return ""
        if f.is_integer():
            return f"{int(f)}h"
        return f"{f:.1f}h"

    s = str(raw).strip()
    if not s:
        return ""

    # bare number in string
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            f = float(s)
            if f <= 0:
                return ""
            if f.is_integer():
                return f"{int(f)}h"
            return f"{f:.1f}h"
        except Exception:
            return ""

    # normalize words
    s2 = s.lower()
    s2 = s2.replace("hours", "h").replace("hour", "h")
    s2 = s2.replace("minutes", "min").replace("minute", "min")
    s2 = re.sub(r"\s+", " ", s2).strip()

    # tidy "2 h" -> "2h"
    s2 = re.sub(r"(\d)\s*h\b", r"\1h", s2)
    s2 = re.sub(r"(\d)\s*min\b", r"\1min", s2)

    # if it still has no unit, keep as-is (but short)
    return s2


# ----------------------------
# Main renderer
# ----------------------------

def render_poi_cards(
    pdf: Any,
    pois: List[Dict[str, Any]],
    *,
    get_photo_path: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None,
    safe_text: Optional[Callable[[Any, int], str]] = None,
    max_cards: int = 6,
    cards_per_page: int = 4,
) -> None:
    """
    Render POIs as 2x2 booking-style cards with rounded photos.

    - Uses 4 cards per page (2 columns x 2 rows).
    - Will add pages as needed.
    - Leaves the cursor after the rendered cards so the existing PDF flow can continue.
    """
    if not pois:
        return

    get_photo_path = get_photo_path or (lambda p: p.get("photo_path") or p.get("local_photo_path"))
    safe_text = safe_text or (lambda t, max_length=300: str(t)[:max_length] if t is not None else "")

    # Theme/colors (match the screenshot style)
    C_TITLE = (44, 62, 80)     # dark slate
    C_MUTED = (127, 140, 141)  # muted gray
    C_BORDER = (220, 224, 229) # light border
    C_PILL = (13, 44, 71)      # dark blue pill

    l_margin = float(getattr(pdf, "l_margin", 15))
    r_margin = float(getattr(pdf, "r_margin", 15))
    page_w = float(getattr(pdf, "w", 210))
    page_h = float(getattr(pdf, "h", 297))
    b_margin = float(getattr(pdf, "b_margin", 15))

    usable_w = page_w - l_margin - r_margin
    gap_x = 10.0
    gap_y = 14.0
    card_w = (usable_w - gap_x) / 2.0

    # Start y
    def ensure_space(min_h: float) -> None:
        if float(pdf.get_y()) + min_h > page_h - b_margin:
            pdf.add_page()

    # Minimum height for 1 row of cards (to avoid starting at bottom)
    min_row_h = 120.0
    ensure_space(min_row_h)

    # We'll compute a stable card height based on available room (clamped)
    start_y = float(pdf.get_y())
    avail_h = (page_h - b_margin) - start_y
    # Prefer ~2 rows per page
    card_h = max(118.0, min(132.0, (avail_h - gap_y) / 2.0))

    img_h = 52.0
    img_pad = 6.0
    corner_r = 7.0

    # paginate
    shown = 0
    pois_to_show = pois[:max_cards]

    while shown < len(pois_to_show):
        # On each page, we attempt up to 4 cards (2x2)
        ensure_space(card_h)  # at least one row
        page_start_y = float(pdf.get_y())
        # If we are mid-page and cannot fit 2 rows, move to next page for clean grid
        if page_start_y + (2 * card_h + gap_y) > page_h - b_margin and (len(pois_to_show) - shown) > 2:
            pdf.add_page()
            page_start_y = float(pdf.get_y())

        x0 = l_margin
        y0 = page_start_y


        cards_on_page = 0
        for slot in range(cards_per_page):
            if shown >= len(pois_to_show):
                break
            row = slot // 2
            col = slot % 2

            cx = x0 + col * (card_w + gap_x)
            cy = y0 + row * (card_h + gap_y)

            # If this row doesn't fit, push to new page
            if cy + card_h > page_h - b_margin:
                pdf.add_page()
                x0 = l_margin
                y0 = float(pdf.get_y())
                cx = x0 + col * (card_w + gap_x)
                cy = y0 + row * (card_h + gap_y)

            poi = pois_to_show[shown]
            shown += 1


            cards_on_page += 1
            # Card background/border
            try:
                pdf.set_draw_color(*C_BORDER)
                pdf.set_fill_color(255, 255, 255)
                pdf.rect(cx, cy, card_w, card_h, style="DF")
            except Exception:
                pdf.rect(cx, cy, card_w, card_h)

            inner_x = cx + img_pad
            inner_w = card_w - 2 * img_pad

            # Photo
            photo_path = None
            try:
                photo_path = get_photo_path(poi)
            except Exception:
                photo_path = None

            if photo_path and os.path.exists(photo_path):
                rounded = _rounded_image_to_temp(photo_path, inner_w, img_h, radius_mm=corner_r)
                try:
                    pdf.image(rounded or photo_path, x=inner_x, y=cy + img_pad, w=inner_w, h=img_h)
                except Exception:
                    pass
            else:
                # placeholder
                try:
                    pdf.set_draw_color(*C_BORDER)
                    pdf.rect(inner_x, cy + img_pad, inner_w, img_h)
                    pdf.set_text_color(*C_MUTED)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_xy(inner_x, cy + img_pad + img_h / 2 - 3)
                    pdf.cell(inner_w, 6, "Photo", align="C")
                except Exception:
                    pass

            # Text area start
            ty = cy + img_pad + img_h + 6.0
            tx = inner_x
            tw = inner_w

            name = safe_text(poi.get("name") or poi.get("title") or "POI", 80)
            desc = safe_text(poi.get("description") or poi.get("summary") or "", 220)

            # Title (1-2 lines)
            pdf.set_text_color(*C_TITLE)
            pdf.set_font("Helvetica", "B", 13)
            title_lines = _wrap_lines(pdf, name, tw, max_lines=2)
            pdf.set_xy(tx, ty)
            pdf.multi_cell(tw, 6.2, "\n".join(title_lines))
            ty = float(pdf.get_y()) + 1.0

            # Description (up to 3 lines)
            if desc:
                pdf.set_text_color(*C_MUTED)
                pdf.set_font("Helvetica", "", 9.5)
                d_lines = _wrap_lines(pdf, desc, tw, max_lines=3)
                pdf.set_xy(tx, ty)
                pdf.multi_cell(tw, 4.4, "\n".join(d_lines))
                ty = float(pdf.get_y()) + 2.0

            # Rating pill + avg time + reviews
            rating = _pick_rating(poi)
            reviews = _pick_review_count(poi)
            avg_time_raw = poi.get("avg_time_spent") or poi.get("avg_time") or poi.get("time_spent") or poi.get("recommended_duration")
            avg_time = _format_avg_time(avg_time_raw)

            pill_w = 18.0
            pill_h = 10.0
            pill_y = min(ty, cy + card_h - 24.0)

            # pill
            try:
                pdf.set_fill_color(*C_PILL)
                pdf.set_draw_color(*C_PILL)
                pdf.rect(tx, pill_y, pill_w, pill_h, style="F")
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 9.5)
                pill_txt = f"{rating:.1f}" if rating is not None else "—"
                pdf.set_xy(tx, pill_y + 2.2)
                pdf.cell(pill_w, 6, pill_txt, align="C")
            except Exception:
                pass

            # right of pill
            info_x = tx + pill_w + 6.0
            info_w = tw - (pill_w + 6.0)
            pdf.set_text_color(*C_TITLE)
            pdf.set_font("Helvetica", "", 10)

            avg_txt = f"Avg time: {avg_time}" if avg_time else "Avg time: —"
            pdf.set_xy(info_x, pill_y + 0.2)
            pdf.cell(info_w, 5, avg_txt)

            # reviews line
            pdf.set_text_color(*C_MUTED)
            pdf.set_font("Helvetica", "", 9.5)
            rev_txt = f"{reviews:,} reviews" if reviews else ""
            pdf.set_xy(info_x, pill_y + 5.6)
            pdf.cell(info_w, 5, rev_txt)

        # Move cursor to below the rendered rows on this page (1 row if <=2 cards, else 2 rows)
        rows_used = 1 if cards_on_page <= 2 else 2
        next_y = y0 + rows_used * card_h + (gap_y if rows_used == 2 else 0) + 2
        pdf.set_xy(l_margin, next_y)
