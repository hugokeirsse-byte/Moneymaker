"""
text_applicator.py — Applique la typographie sur les images Redbubble générées.

Principe : FLUX génère l'illustration pure (sans texte). Le CDC contient un bloc
`typography` qui décrit chaque couche de texte à ajouter (position, police,
taille, couleur). Ce module lit ce bloc et applique le texte avec PIL.

Types de placement supportés :
  - top_arc / bottom_arc : texte courbe pour les badges/guild seals (Style 2)
  - center / top / bottom : texte centré horizontal à une hauteur relative
  - annotation : label positionné à des coordonnées x,y relatives (Style 3)
  - italic_caption : légende italique sous le sujet (Style 1 naturaliste)

Polices disponibles (basées sur les polices système) :
  serif_bold | serif | serif_italic | serif_bold_italic |
  mono | mono_bold | sans | sans_bold
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Registre des polices ──────────────────────────────────────────────────────

_FONT_PATHS = {
    "serif":            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "serif_bold":       "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "serif_italic":     "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "serif_bold_italic":"/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf",
    "mono":             "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "mono_bold":        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "sans":             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "sans_bold":        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "free_serif":       "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "free_serif_italic":"/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
    "free_serif_bold":  "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
}

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def _get_font(style: str, size_pt: int) -> ImageFont.FreeTypeFont:
    key = (style, size_pt)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    path = _FONT_PATHS.get(style)
    if path and os.path.exists(path):
        font = ImageFont.truetype(path, size_pt)
    else:
        logger.warning("[text_applicator] police '%s' introuvable — repli PIL défaut", style)
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _parse_color(color: str) -> Tuple[int, int, int, int]:
    """Convertit un #HEXCODE en RGBA. Supporte aussi 'black', 'white', etc."""
    color = color.strip()
    if color.startswith("#"):
        h = color.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b, 255)
        if len(h) == 8:
            r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
            return (r, g, b, a)
    named = {"black": (0, 0, 0, 255), "white": (255, 255, 255, 255),
             "transparent": (0, 0, 0, 0)}
    return named.get(color.lower(), (0, 0, 0, 255))


# ── Texte droit (simple) ──────────────────────────────────────────────────────

def _apply_straight_text(
    img: Image.Image,
    text: str,
    position: str,          # "top" | "bottom" | "center" | "top_left" | "bottom_right"
    font: ImageFont.FreeTypeFont,
    color: Tuple,
    y_offset_pct: float = 0.0,   # décalage vertical en % de la hauteur (signed)
    x_offset_pct: float = 0.0,   # décalage horizontal en % de la largeur
    max_width_pct: float = 0.85,  # largeur max du texte en % de l'image
    letter_spacing: int = 0,
) -> None:
    """Dessine du texte centré à une position relative sur l'image."""
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # Mesure la largeur du texte
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Réduction automatique si le texte dépasse la largeur max
    max_w = int(W * max_width_pct)
    if tw > max_w:
        scale = max_w / tw
        new_size = max(12, int(font.size * scale))
        font = _get_font(getattr(font, "_font_style", "serif"), new_size)
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

    if position in ("top", "top_left", "top_right"):
        y_base = int(H * 0.06)
    elif position in ("bottom", "bottom_left", "bottom_right"):
        y_base = int(H * 0.90) - th
    else:  # center
        y_base = (H - th) // 2

    y = y_base + int(H * y_offset_pct)
    x = (W - tw) // 2 + int(W * x_offset_pct)

    if "left" in position:
        x = int(W * 0.05)
    elif "right" in position:
        x = W - tw - int(W * 0.05)

    draw.text((x, y), text, font=font, fill=color)


# ── Texte courbe (arc) ─────────────────────────────────────────────────────────

def _apply_arc_text(
    img: Image.Image,
    text: str,
    arc_type: str,           # "top_arc" | "bottom_arc"
    font: ImageFont.FreeTypeFont,
    color: Tuple,
    arc_radius_pct: float = 38.0,   # rayon en % de la largeur de l'image
    gap_deg: float = 10.0,          # espace vide en bas/haut de l'arc (degrés)
    letter_spacing_deg: float = 0.0,
) -> None:
    """
    Dessine du texte le long d'un arc circulaire.

    Algo : chaque caractère est rendu dans une surface temporaire,
    pivoté selon son angle sur l'arc, puis collé sur l'image principale.
    """
    W, H = img.size
    cx, cy = W // 2, H // 2
    radius = int(W * arc_radius_pct / 100)

    # Mesure chaque caractère
    char_widths = []
    for ch in text:
        bb = font.getbbox(ch)
        char_widths.append(bb[2] - bb[0])
    total_w = sum(char_widths)

    # Angle total couvert par le texte (en radians) basé sur la longueur d'arc
    total_arc_rad = total_w / radius
    gap_rad = math.radians(gap_deg)

    if arc_type == "top_arc":
        # Le texte court sur la partie SUPÉRIEURE du cercle
        # angle 0 = 12h, sens horaire positif
        start_angle = -math.pi / 2 - total_arc_rad / 2
        char_direction = 1
        baseline_offset = -font.size  # les caractères poussent vers l'extérieur
    else:
        # bottom_arc : texte sur la partie INFÉRIEURE, lettres pointent vers le bas
        start_angle = math.pi / 2 - total_arc_rad / 2
        char_direction = 1
        baseline_offset = 0

    current_angle = start_angle

    for i, (ch, cw) in enumerate(zip(text, char_widths)):
        # Centre de ce caractère sur l'arc
        char_arc = cw / radius
        angle = current_angle + char_arc / 2

        # Position du centre du caractère
        if arc_type == "top_arc":
            px = cx + radius * math.sin(angle)
            py = cy - radius * math.cos(angle)
            rot_deg = math.degrees(angle)
        else:
            px = cx + radius * math.sin(angle)
            py = cy - radius * math.cos(angle)
            rot_deg = math.degrees(angle) + 180  # lettres pointent vers centre

        # Rendu du caractère dans une surface temporaire
        ch_h = font.size + 4
        ch_surf_w = max(cw + 4, ch_h)
        ch_surf = Image.new("RGBA", (ch_surf_w * 2, ch_h * 2), (0, 0, 0, 0))
        ch_draw = ImageDraw.Draw(ch_surf)
        ch_draw.text((ch_surf_w // 2, ch_h // 2), ch, font=font, fill=color, anchor="mm")

        # Rotation
        rotated = ch_surf.rotate(-rot_deg, expand=True, resample=Image.BICUBIC)

        # Collage sur l'image principale
        paste_x = int(px) - rotated.width // 2
        paste_y = int(py) - rotated.height // 2
        img.paste(rotated, (paste_x, paste_y), rotated)

        current_angle += char_arc


# ── Texte annotation (Style 3 diagrammes) ────────────────────────────────────

def _apply_annotation(
    img: Image.Image,
    text: str,
    x_pct: float,       # 0.0 - 1.0 depuis gauche
    y_pct: float,       # 0.0 - 1.0 depuis haut
    font: ImageFont.FreeTypeFont,
    color: Tuple,
    anchor: str = "lm", # lm=left-middle, rm=right-middle, mm=center
    leader_to_pct: Optional[Tuple[float, float]] = None,  # endpoint du trait guide
    leader_color: Optional[Tuple] = None,
) -> None:
    """
    Place un label d'annotation à des coordonnées relatives.
    Optionnellement dessine un trait guide vers un point de l'image.
    """
    draw = ImageDraw.Draw(img)
    W, H = img.size
    x, y = int(x_pct * W), int(y_pct * H)

    if leader_to_pct and leader_color:
        lx, ly = int(leader_to_pct[0] * W), int(leader_to_pct[1] * H)
        draw.line([(x, y), (lx, ly)], fill=leader_color or color, width=2)

    draw.text((x, y), text, font=font, fill=color, anchor=anchor)


# ── Application d'un bloc typography complet ─────────────────────────────────

def apply_typography(
    image_path: str,
    typography_spec: Dict,
    output_path: Optional[str] = None,
) -> str:
    """
    Applique toutes les couches typographiques définies dans `typography_spec`
    sur l'image `image_path`.

    Args:
        image_path:      Chemin vers le PNG source.
        typography_spec: Dict issu du champ `typography` du CDC.
        output_path:     Chemin de sortie. Si None, écrase l'original.

    Returns:
        Le chemin du fichier résultant.
    """
    if not typography_spec.get("apply", True):
        logger.debug("[text_applicator] typography.apply=false → aucun texte ajouté")
        return image_path

    layers = typography_spec.get("layers", [])
    if not layers:
        return image_path

    img = Image.open(image_path).convert("RGBA")

    for layer in layers:
        text = layer.get("text", "").strip()
        if not text:
            continue

        font_style = layer.get("font_style", "serif")
        # Convertit la taille en px à partir de pt (approximation 96dpi→300dpi)
        size_pt = layer.get("size_pt", 60)
        # Les images sont 4500px = 15" à 300dpi → 1pt ≈ 4.17px à 300dpi
        size_px = max(12, int(size_pt * 4.17))
        # Mais on adapte selon la résolution réelle de l'image
        W, H = img.size
        scale = W / 4500
        size_px = max(12, int(size_px * scale))

        font = _get_font(font_style, size_px)
        color = _parse_color(layer.get("color", "#000000"))

        position = layer.get("position", "bottom")

        try:
            if position in ("top_arc", "bottom_arc"):
                _apply_arc_text(
                    img, text, position, font, color,
                    arc_radius_pct=layer.get("arc_radius_pct", 38.0),
                    gap_deg=layer.get("gap_deg", 8.0),
                )
            elif position == "annotation":
                _apply_annotation(
                    img, text,
                    x_pct=layer.get("x_pct", 0.5),
                    y_pct=layer.get("y_pct", 0.5),
                    font=font, color=color,
                    anchor=layer.get("anchor", "lm"),
                    leader_to_pct=layer.get("leader_to_pct"),
                    leader_color=_parse_color(layer.get("leader_color", layer.get("color", "#888888"))),
                )
            else:
                _apply_straight_text(
                    img, text, position, font, color,
                    y_offset_pct=layer.get("y_offset_pct", 0.0),
                    x_offset_pct=layer.get("x_offset_pct", 0.0),
                    max_width_pct=layer.get("max_width_pct", 0.85),
                )
        except Exception as exc:
            logger.warning("[text_applicator] couche '%s' échouée: %s", text[:40], exc)

    out = output_path or image_path
    # Sauvegarde en PNG 300 DPI en conservant le profil sRGB
    img_rgb = img.convert("RGB")
    img_rgb.save(out, format="PNG", dpi=(300, 300))
    logger.info("[text_applicator] texte appliqué → %s", out)
    return out


# ── Auto-typographie pour planches naturalistes ───────────────────────────────

def _auto_naturalist_typography(brief: Dict) -> Dict:
    """
    Auto-génère les layers de typographie pour une planche naturaliste dont le
    CDC ne contient pas de bloc typography.layers (Gemini n'a pas rempli le champ).

    Produit :
      - Nom commun   → position "top" en serif
      - Nom sci.     → position "bottom" en serif_italic (extrait du prompt FLUX)
    """
    name = brief.get("name", "")
    common_name = re.sub(
        r"\s*\b(?:plate|planche|specimen|anatomy)\b\s*$",
        "", name, flags=re.IGNORECASE
    ).strip()

    # Cherche le nom scientifique dans le positive_prompt
    positive_prompt = (
        brief.get("ai_generation", {}).get("positive_prompt", "")
        or brief.get("positive_prompt", "")
    )
    sci_match = re.search(r"\b([A-Z][a-z]+(?:\s+[a-z]+){1,2})\b", positive_prompt)
    scientific_name = sci_match.group(1) if sci_match else ""
    if scientific_name.lower() == common_name.lower():
        scientific_name = ""

    # Couleur texte sombre depuis la palette du CDC
    vd = brief.get("visual_direction", {})
    colors_raw = vd.get("color_primary", vd.get("color_palette", {}).get("primary", []))
    text_color = "#1A1A2E"
    for c_str in colors_raw:
        hex_m = re.search(r"#([0-9A-Fa-f]{6})", str(c_str))
        if hex_m:
            h = hex_m.group(1)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            if 0.299 * r + 0.587 * g + 0.114 * b < 100:
                text_color = f"#{h}"
                break

    layers: List[Dict] = []
    if common_name:
        layers.append({
            "text": common_name,
            "position": "top",
            "font_style": "serif",
            "size_pt": 32,
            "color": text_color,
            "y_offset_pct": 0.01,
            "max_width_pct": 0.80,
        })
    if scientific_name:
        layers.append({
            "text": scientific_name,
            "position": "bottom",
            "font_style": "serif_italic",
            "size_pt": 26,
            "color": text_color,
            "y_offset_pct": -0.02,
            "max_width_pct": 0.72,
        })

    return {"apply": bool(layers), "layers": layers}


# ── Correspondance image → CDC via slug ───────────────────────────────────────

def _slug(name: str) -> str:
    """Normalise un nom de niche en slug (minuscules, tirets)."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _find_cdc_for_image(image_path: str, briefs: List[Dict]) -> Optional[Dict]:
    """Trouve le brief CDC correspondant à un fichier image via le slug du nom."""
    stem = Path(image_path).stem.lower()
    for brief in briefs:
        name = brief.get("name", "")
        if not name:
            continue
        s = _slug(name)
        if s in stem or stem.startswith(s[:20]):
            return brief
    return None


# ── Application batch ─────────────────────────────────────────────────────────

def batch_apply_typography(
    cdc_json_path: str,
    images_dir: str,
    output_dir: Optional[str] = None,
    overwrite: bool = False,
) -> List[str]:
    """
    Applique la typographie de chaque brief CDC sur l'image correspondante.

    Args:
        cdc_json_path: Chemin vers le CDC JSON (format Redbubble).
        images_dir:    Dossier contenant les PNG générés.
        output_dir:    Dossier de sortie (None = écrase les originaux).
        overwrite:     Si True, re-applique même si le fichier existe déjà.

    Returns:
        Liste des chemins de fichiers traités.
    """
    with open(cdc_json_path, encoding="utf-8") as f:
        cdc = json.load(f)

    briefs = cdc.get("briefs", cdc) if isinstance(cdc, dict) else cdc

    images = sorted(Path(images_dir).glob("*.png"))
    if not images:
        logger.warning("[text_applicator] aucune image PNG trouvée dans %s", images_dir)
        return []

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    processed = []
    skipped = 0

    for img_path in images:
        brief = _find_cdc_for_image(str(img_path), briefs)
        if brief is None:
            logger.debug("[text_applicator] aucun CDC trouvé pour %s", img_path.name)
            continue

        typography = brief.get("typography")
        # Auto-génère la typographie pour les planches naturalistes sans layers
        if not typography or not typography.get("apply", False):
            name = brief.get("name", "")
            if any(kw in name.lower() for kw in ("plate", "planche", "specimen", "anatomy")):
                typography = _auto_naturalist_typography(brief)
            if not typography or not typography.get("apply", False):
                skipped += 1
                continue

        if output_dir:
            out_path = str(Path(output_dir) / img_path.name)
        else:
            out_path = str(img_path)

        if not overwrite and output_dir and Path(out_path).exists():
            logger.debug("[text_applicator] déjà traité: %s", img_path.name)
            processed.append(out_path)
            continue

        try:
            result = apply_typography(str(img_path), typography, out_path)
            processed.append(result)
            logger.info("[text_applicator] ✓ %s", img_path.name)
        except Exception as exc:
            logger.error("[text_applicator] ✗ %s: %s", img_path.name, exc)

    logger.info(
        "[text_applicator] terminé: %d traités, %d sans typographie",
        len(processed), skipped,
    )
    return processed


# ── Érase texte FLUX (Gemini Vision + PIL fill) ───────────────────────────────

def _estimate_bg_color(img: Image.Image) -> Tuple[int, int, int]:
    """Estime la couleur de fond en échantillonnant les 4 coins de l'image."""
    W, H = img.size
    patch = max(10, min(40, W // 100))
    corners = [
        img.crop((0, 0, patch, patch)),
        img.crop((W - patch, 0, W, patch)),
        img.crop((0, H - patch, patch, H)),
        img.crop((W - patch, H - patch, W, H)),
    ]
    r_all, g_all, b_all = [], [], []
    for c in corners:
        for px in c.convert("RGB").getdata():
            r_all.append(px[0])
            g_all.append(px[1])
            b_all.append(px[2])
    n = len(r_all)
    return (sum(r_all) // n, sum(g_all) // n, sum(b_all) // n)


def _detect_text_regions_gemini(image_path: str) -> List[Dict]:
    """
    Détecte les régions de texte dans une image via Gemini Vision.
    Retourne une liste de {x_min, y_min, x_max, y_max} en pourcentages [0-100].
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("[text_applicator] GEMINI_API_KEY absente — détection texte ignorée")
        return []

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        img_pil = Image.open(image_path).convert("RGB")

        prompt = (
            "Find ALL text regions in this image (titles, labels, captions, scientific names, watermarks). "
            "Return a JSON array: "
            '[{"text":"...", "x_min":N, "y_min":N, "x_max":N, "y_max":N}] '
            "where N are percentages of image dimensions (0=top-left, 100=bottom-right). "
            "Add 3% padding around each region. "
            "If no text is visible, return []. Return ONLY the JSON array, no markdown."
        )

        response = model.generate_content([img_pil, prompt])
        raw = response.text.strip()
        if "```" in raw:
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

        regions = json.loads(raw)
        logger.info("[text_applicator] %d région(s) de texte détectée(s) dans %s",
                    len(regions), Path(image_path).name)
        return regions
    except Exception as exc:
        logger.warning("[text_applicator] détection texte Gemini échouée: %s", exc)
        return []


def _fill_text_region(
    img: Image.Image,
    region: Dict,
    bg_color: Tuple[int, int, int],
    padding_px: int = 6,
) -> Image.Image:
    """
    Efface une région de texte en la remplissant avec la couleur de fond.
    Un léger flou gaussien est appliqué sur les bords pour lisser la transition.
    """
    from PIL import ImageFilter

    W, H = img.size
    x_min = max(0, int(region.get("x_min", 0) / 100 * W) - padding_px)
    y_min = max(0, int(region.get("y_min", 0) / 100 * H) - padding_px)
    x_max = min(W, int(region.get("x_max", 100) / 100 * W) + padding_px)
    y_max = min(H, int(region.get("y_max", 100) / 100 * H) + padding_px)

    if x_max <= x_min or y_max <= y_min:
        return img

    mode = img.mode
    img_work = img.convert("RGB")
    draw = ImageDraw.Draw(img_work)
    draw.rectangle([x_min, y_min, x_max, y_max], fill=bg_color)

    # Légère zone de flou pour les transitions de bord
    blur_pad = 12
    bx0 = max(0, x_min - blur_pad)
    by0 = max(0, y_min - blur_pad)
    bx1 = min(W, x_max + blur_pad)
    by1 = min(H, y_max + blur_pad)
    edge_patch = img_work.crop((bx0, by0, bx1, by1))
    edge_patch = edge_patch.filter(ImageFilter.GaussianBlur(radius=5))
    # Ne coller que les bords floutés, pas le centre (déjà propre)
    center_patch = img_work.crop((x_min, y_min, x_max, y_max))
    img_work.paste(edge_patch, (bx0, by0))
    img_work.paste(center_patch, (x_min, y_min))

    return img_work.convert(mode) if mode == "RGBA" else img_work


def erase_flux_text(
    image_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Détecte et efface le texte rendu par FLUX dans une illustration.

    Utilise Gemini Vision pour localiser les régions de texte, puis les
    remplace par la couleur de fond estimée via PIL (aucun coût Runware).

    Args:
        image_path:  Chemin vers le PNG source.
        output_path: Chemin de sortie (None = écrase l'original).

    Returns:
        Chemin du fichier résultant.
    """
    regions = _detect_text_regions_gemini(image_path)
    if not regions:
        if output_path and output_path != image_path:
            import shutil
            shutil.copy2(image_path, output_path)
        return output_path or image_path

    img = Image.open(image_path)
    bg_color = _estimate_bg_color(img)
    logger.info("[text_applicator] couleur de fond estimée: rgb%s", bg_color)

    for region in regions:
        try:
            img = _fill_text_region(img, region, bg_color)
        except Exception as exc:
            logger.warning("[text_applicator] erreur érase région: %s", exc)

    out = output_path or image_path
    img_out = img.convert("RGB")
    img_out.save(out, format="PNG", dpi=(300, 300))
    logger.info("[text_applicator] texte effacé → %s", out)
    return out


def batch_fix_text(
    cdc_json_path: str,
    images_dir: str,
    output_dir: Optional[str] = None,
    overwrite: bool = False,
    erase_only: bool = False,
) -> List[str]:
    """
    Pipeline complet de correction du texte FLUX :
      1. Détecte et efface les régions de texte via Gemini Vision + PIL
      2. Applique la typographie propre définie dans le CDC (si erase_only=False)

    Args:
        cdc_json_path: CDC JSON Redbubble.
        images_dir:    Dossier des PNG sources (illustrations avec texte FLUX).
        output_dir:    Dossier de sortie (None = écrase les originaux).
        overwrite:     Re-traite même si le fichier de sortie existe déjà.
        erase_only:    Si True, efface le texte sans appliquer la typo CDC.

    Returns:
        Liste des chemins de fichiers traités.
    """
    with open(cdc_json_path, encoding="utf-8") as f:
        cdc = json.load(f)

    briefs = cdc.get("briefs", cdc) if isinstance(cdc, dict) else cdc
    images = sorted(Path(images_dir).glob("*.png"))

    if not images:
        logger.warning("[text_applicator] aucune image PNG dans %s", images_dir)
        return []

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    processed = []

    for img_path in images:
        if output_dir:
            out_path = str(Path(output_dir) / img_path.name)
        else:
            out_path = str(img_path)

        if not overwrite and output_dir and Path(out_path).exists():
            processed.append(out_path)
            continue

        try:
            logger.info("[text_applicator] fix texte : %s", img_path.name)
            intermediate = erase_flux_text(str(img_path), out_path)

            if not erase_only:
                brief = _find_cdc_for_image(str(img_path), briefs)
                if brief:
                    typography = brief.get("typography")
                    if typography and typography.get("apply", False):
                        apply_typography(intermediate, typography, out_path)
                        logger.info("[text_applicator] typo CDC appliquée : %s", img_path.name)

            processed.append(out_path)
        except Exception as exc:
            logger.error("[text_applicator] échec %s: %s", img_path.name, exc)

    logger.info("[text_applicator] batch_fix_text terminé: %d fichiers traités", len(processed))
    return processed
