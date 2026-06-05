"""
VisualAuditor — audit Gemini Vision des images générées.

Pour chaque PNG dans output/spoonflower/, envoie l'image à Gemini Vision
et retourne un rapport structuré : score /100 + liste précise de problèmes.

Critères (100 pts) :
  1. Anatomie / Intégrité   (25 pts) — membres corrects, objets reconnaissables
  2. Cohérence visuelle     (20 pts) — pas de formes ambiguës ou semi-formées
  3. Typographie            (15 pts) — texte lisible ou absent (pseudo-texte = 0)
  4. Fidélité style         (20 pts) — flat 2D, zéro 3D / aquarelle / gradient
  5. Layout / Espacement    (10 pts) — distribution équilibrée
  6. Tuilage seamless       (10 pts) — bords raccordables (test 2×2)

Requiert : GEMINI_API_KEY + Pillow + requests
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompts Gemini Vision
# ─────────────────────────────────────────────────────────────────────────────

_AUDIT_PROMPT = """\
You are an expert surface pattern design quality auditor for Spoonflower (fabric/wallpaper POD platform).
Evaluate the attached pattern image strictly and return a JSON quality report.

PATTERN NAME: {cdc_name}
INTENDED STYLE: {style_hint}

SCORING CRITERIA (100 pts total):

1. ANATOMY & OBJECT INTEGRITY (25 pts)
   Every animal/creature must have the correct number of limbs, wings, fins — no extras, no missing.
   Objects must be complete and recognizable. No morphed, melted, or half-formed shapes.
   Common failures: bird with 3+ legs, insect with extra wings, horse with 5 legs, fish with 3 tails,
   a fox posture that looks like a different animal, object that is only partially rendered.

2. VISUAL COHERENCE (20 pts)
   All elements must resolve into clearly identifiable, recognizable objects.
   No garbled, dreamlike, or ambiguous blobs that could be two things at once.
   Common failures: shape between two objects with no clear reading, element cut off mid-form with no clear identity.

3. TYPOGRAPHY & TEXT (15 pts)
   If no text is present: award full 15 pts.
   If decorative label shapes with no readable characters: award full 15 pts.
   If actual letters/numbers are present: are they all correct and legible?
   Common failures: alphabet blocks with deformed letters, bottle labels with garbled pseudo-text strings,
   tin label with nonsense character sequences.

4. STYLE FIDELITY (20 pts)
   Must be flat 2D illustration — solid color fills, clean vector-like outlines, no gradients.
   No 3D bevel/emboss, no watercolor bleed, no airbrushed shadows, no photorealistic rendering.
   Common failures: glossy/shiny object highlights, soft blurred edges, gradient fill inside shapes,
   drop shadows behind elements.

5. LAYOUT & SPACING (10 pts)
   Elements must be well-distributed across the full image surface.
   No large empty zones alongside very crowded zones in the same image.
   Common failures: all motifs clustered in the center third, large blank corners,
   excessive overlap making individual elements unreadable.

6. SEAMLESS TILING (10 pts)
   The four edges must match up when the tile is repeated side-by-side.
   Elements near edges must continue cleanly on the opposite side.
   Common failures: element abruptly cut in half at right edge with no matching start at left edge,
   background color shift at boundaries, horizontal or vertical seam line visible.

Return ONLY valid JSON with no markdown code fence and no text before or after:
{{
  "score": <integer 0-100>,
  "anatomy_issues": [<"one specific issue per string"> or []],
  "coherence_issues": [<"one specific issue per string"> or []],
  "text_issues": [<"one specific issue per string"> or []],
  "style_issues": [<"one specific issue per string"> or []],
  "layout_issues": [<"one specific issue per string"> or []],
  "tiling_issues": [<"one specific issue per string"> or []],
  "verdict": <"pass" if score>=75 else "fix" if score>=50 else "reject">,
  "summary": <"one sentence in French summarizing the overall quality">
}}
"""

_TILING_PROMPT = """\
This image shows a 2×2 tiled arrangement of the same repeating pattern.
Focus on the center horizontal seam and center vertical seam where tiles meet.

Do the tiles join seamlessly, or are there visible defects at the seams?

Return ONLY valid JSON:
{{
  "seams_visible": <true if hard seams are clearly visible, false if seamless>,
  "seam_description": <"one sentence describing what you observe at the seam lines">,
  "tiling_score": <integer 0-10: 10=perfectly seamless, 5=minor artifacts, 0=obvious grid seam>
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Auditor class
# ─────────────────────────────────────────────────────────────────────────────

class VisualAuditor:
    """Audit visuel via Gemini Vision pour valider les images Spoonflower."""

    GEMINI_MODEL = "gemini-2.0-flash"
    PREVIEW_MAX = 1024   # px max side for main audit (saves tokens)
    TILE_CELL   = 512    # px per cell in 2×2 tiling test

    def __init__(self):
        self._api_key = os.environ.get("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ── Image helpers ──────────────────────────────────────────────────────────

    def _resize_png(self, image_bytes: bytes, max_px: int) -> bytes:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img.thumbnail((max_px, max_px), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
        except Exception:
            return image_bytes

    def _make_2x2(self, image_bytes: bytes) -> bytes:
        """Create a 2×2 tiled PNG for seam assessment."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = img.resize((self.TILE_CELL, self.TILE_CELL), Image.LANCZOS)
            canvas = Image.new("RGB", (self.TILE_CELL * 2, self.TILE_CELL * 2))
            for dx in range(2):
                for dy in range(2):
                    canvas.paste(img, (dx * self.TILE_CELL, dy * self.TILE_CELL))
            buf = io.BytesIO()
            canvas.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return image_bytes

    # ── Gemini Vision call ─────────────────────────────────────────────────────

    def _gemini_vision(self, image_bytes: bytes, prompt: str) -> Optional[str]:
        try:
            import requests
            b64 = base64.b64encode(image_bytes).decode()
            payload = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                        {"text": prompt},
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                    "responseMimeType": "application/json",
                },
            }
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.GEMINI_MODEL}:generateContent?key={self._api_key}"
            )
            r = requests.post(url, json=payload, timeout=45)
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            logger.error("[auditor] Gemini Vision erreur: %s", exc)
            return None

    def _parse_json(self, raw: Optional[str]) -> Optional[dict]:
        if not raw:
            return None
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
            logger.warning("[auditor] JSON parse failed: %s", raw[:200])
            return None

    # ── Public API ─────────────────────────────────────────────────────────────

    def audit_image(
        self,
        image_bytes: bytes,
        cdc_name: str,
        style_hint: str = "",
    ) -> dict:
        """
        Audit une image via Gemini Vision.

        Returns dict with: score (0-100), issues by category, verdict, summary.
        score=-1 si erreur.
        """
        if not self.is_available():
            return {"score": -1, "error": "GEMINI_API_KEY absent"}

        # 1. Main quality audit
        resized = self._resize_png(image_bytes, self.PREVIEW_MAX)
        prompt = _AUDIT_PROMPT.format(
            cdc_name=cdc_name,
            style_hint=style_hint or "flat 2D seamless surface pattern for fabric and wallpaper",
        )
        result = self._parse_json(self._gemini_vision(resized, prompt))
        if result is None:
            return {"score": -1, "error": "Gemini Vision call failed or JSON invalid"}

        # 2. Tiling check (2×2 tile)
        tiled = self._make_2x2(image_bytes)
        tiling = self._parse_json(self._gemini_vision(tiled, _TILING_PROMPT))
        if tiling:
            result["tiling_check"] = tiling
            tiling_score_10 = tiling.get("tiling_score", 5)
            if tiling_score_10 <= 3 and not result.get("tiling_issues"):
                result.setdefault("tiling_issues", [])
                desc = tiling.get("seam_description", "Coutures visibles dans le test 2×2")
                result["tiling_issues"].append(desc)
            # Penalize score for bad tiling
            if tiling.get("seams_visible") and tiling_score_10 <= 4:
                result["score"] = max(0, result.get("score", 50) - 8)

        # Normalise verdict to match actual score
        score = result.get("score", 0)
        result["verdict"] = "pass" if score >= 75 else ("fix" if score >= 50 else "reject")

        return result

    def audit_directory(
        self,
        image_dir: str,
        cdc_map: Dict[str, dict],
        output_dir: str = "./reports",
    ) -> Tuple[str, str]:
        """
        Audit tous les PNGs dans image_dir.

        Args:
            image_dir: dossier contenant les PNG Spoonflower
            cdc_map: {safe_cdc_name: brief_dict} pour enrichir le contexte
            output_dir: où sauvegarder rapport MD + JSON

        Returns:
            (md_path, json_path)
        """
        import glob as _glob

        png_files = sorted(_glob.glob(os.path.join(image_dir, "*.png")))
        if not png_files:
            logger.warning("[auditor] Aucune image dans %s", image_dir)
            return "", ""

        logger.info("[auditor] %d images à auditer…", len(png_files))

        results = []
        for filepath in png_files:
            filename = os.path.basename(filepath)
            # Extract CDC safe name: everything before first "___"
            cdc_safe = filename.split("___")[0]
            brief = _find_brief(cdc_safe, cdc_map)
            cdc_name = brief.get("name", cdc_safe) if brief else cdc_safe
            style_hint = ""
            if brief:
                style_hint = brief.get("ai_generation", {}).get("positive_prompt", "")[:150]

            logger.info("[auditor] '%s' (%s)…", cdc_name, filename)
            with open(filepath, "rb") as fh:
                image_bytes = fh.read()

            audit = self.audit_image(image_bytes, cdc_name, style_hint)
            results.append({
                "filename": filename,
                "filepath": filepath,
                "cdc_name": cdc_name,
                "cdc_safe": cdc_safe,
                "audit": audit,
            })

            score = audit.get("score", -1)
            verdict = audit.get("verdict", "?")
            logger.info("[auditor] %s → %d/100 [%s]", cdc_name, score, verdict.upper())

        # Sort by score descending
        results.sort(key=lambda r: r["audit"].get("score", -1), reverse=True)

        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

        json_path = os.path.join(output_dir, f"audit_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)

        md_path = os.path.join(output_dir, f"audit_{ts}.md")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(_render_markdown(results))

        logger.info("[auditor] ✅ Rapport : %s", md_path)
        return md_path, json_path


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_name(text: str) -> str:
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in text)
    return safe.strip().replace(" ", "_").lower()


def _find_brief(cdc_safe: str, cdc_map: Dict[str, dict]) -> Optional[dict]:
    """Fuzzy match: try exact, then prefix, then substring."""
    if cdc_safe in cdc_map:
        return cdc_map[cdc_safe]
    # Prefix match (filename safe names are truncated at 60 chars)
    for key, brief in cdc_map.items():
        if key.startswith(cdc_safe) or cdc_safe.startswith(key[:40]):
            return brief
    return None


def _render_markdown(results: list) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pass_list   = [r for r in results if r["audit"].get("verdict") == "pass"]
    fix_list    = [r for r in results if r["audit"].get("verdict") == "fix"]
    reject_list = [r for r in results if r["audit"].get("verdict") == "reject"]
    error_list  = [r for r in results if r["audit"].get("score", 0) < 0]

    lines = [
        f"# Audit Spoonflower — {ts}",
        "",
        "## Résumé",
        f"| Verdict | Count |",
        f"|---------|-------|",
        f"| ✅ Pass (≥75/100) | **{len(pass_list)}** |",
        f"| ⚠️ Fix (50–74/100) | **{len(fix_list)}** |",
        f"| ❌ Reject (<50/100) | **{len(reject_list)}** |",
        f"| ⛔ Erreur | **{len(error_list)}** |",
        f"| **Total** | **{len(results)}** |",
        "",
        "---",
        "",
        "## Détail par image",
        "",
    ]

    for i, r in enumerate(results, 1):
        audit  = r["audit"]
        score  = audit.get("score", -1)
        verdict = audit.get("verdict", "error")
        cdc    = r["cdc_name"]
        icon   = {"pass": "✅", "fix": "⚠️", "reject": "❌"}.get(verdict, "⛔")

        lines += [
            f"### {i}. {cdc} — {score}/100 {icon}",
            f"**Fichier :** `{r['filename']}`",
            f"**Verdict :** `{verdict.upper()}`",
            f"**Résumé :** {audit.get('summary', '—')}",
            "",
        ]

        categories = [
            ("anatomy_issues",   "🦴 Anatomie"),
            ("coherence_issues", "👁️ Cohérence"),
            ("text_issues",      "🔤 Typographie"),
            ("style_issues",     "🎨 Style"),
            ("layout_issues",    "📐 Layout"),
            ("tiling_issues",    "🔲 Tuilage"),
        ]
        has_issues = False
        for key, label in categories:
            issues = audit.get(key) or []
            if issues:
                has_issues = True
                lines.append(f"- **{label} :** {' | '.join(issues)}")

        if not has_issues:
            lines.append("*Aucun problème détecté.*")
        lines.append("")

        tc = audit.get("tiling_check", {})
        if tc:
            seams_str = "⚠️ Visibles" if tc.get("seams_visible") else "✅ Non visibles"
            ts_score  = tc.get("tiling_score", "?")
            lines.append(f"**Test tuilage 2×2 :** {seams_str} — {ts_score}/10")
            if tc.get("seam_description"):
                lines.append(f"> {tc['seam_description']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Regeneration targets
    to_regen = fix_list + reject_list
    if to_regen:
        lines += [
            "## Régénérations recommandées",
            "",
            "| Priorité | CdC | Score | Problèmes |",
            "|----------|-----|-------|-----------|",
        ]
        for r in sorted(to_regen, key=lambda x: x["audit"].get("score", 0)):
            audit = r["audit"]
            all_issues = []
            for key in ("anatomy_issues", "coherence_issues", "text_issues",
                        "style_issues", "layout_issues", "tiling_issues"):
                all_issues.extend(audit.get(key) or [])
            prio = "❌ Urgent" if audit.get("verdict") == "reject" else "⚠️ Fix"
            issues_str = " / ".join(all_issues[:3]) if all_issues else "—"
            lines.append(
                f"| {prio} | {r['cdc_name']} | {audit.get('score', '?')}/100 | {issues_str} |"
            )
        lines += [
            "",
            "```",
            "# GitHub Actions → mode=generate-best, niche=<nom>, limit=1",
            "```",
            "",
        ]

    return "\n".join(lines)
