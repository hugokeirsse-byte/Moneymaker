#!/usr/bin/env node
/*
 * compose_back_text.js — pose le résumé de 4e de couverture dans le panneau
 * réservé, SANS régénérer l'image FLUX. Itération rapide sur le texte.
 *
 * Entrées :
 *   - le raster du wrap sans texte : <concept>/cover_paperback_base.png
 *   - la géométrie du panneau      : <concept>/<concept>_panel.json
 *   - le texte du résumé           : fichier .txt (ou --text "...")
 *
 * Sortie :
 *   - <concept>/cover_paperback_texte.png  (wrap complet, aplati, 300 DPI)
 *
 * Dépendance : sharp  ->  npm install sharp
 *
 * Exemples :
 *   node compose_back_text.js output/covers/chambre404 resume.txt
 *   node compose_back_text.js output/covers/reflet --text "Elle s'est réveillée…"
 *
 * Note : pour le PDF KDP final avec le résumé, régénère directement via Python
 * (aucun appel Runware, l'art est déjà sauvegardé) :
 *   python3 scripts/covers/compose_cover.py --art art/chambre404.png \
 *       --concept chambre404 --out output/covers --resume resume.txt \
 *       --title "CYCLE 404" --tagline "Et si votre deuil était un décor ?" \
 *       --author "SHIRO KEGESU" --pages 400
 */
"use strict";

const fs = require("fs");
const path = require("path");

let sharp;
try {
  sharp = require("sharp");
} catch (e) {
  console.error("Dépendance manquante : exécute  npm install sharp");
  process.exit(1);
}

// ---- args -----------------------------------------------------------------
const args = process.argv.slice(2);
if (args.length < 1) {
  console.error("Usage: node compose_back_text.js <dossier_concept> [resume.txt|--text \"...\"]");
  process.exit(1);
}
const conceptDir = args[0];
let text = "";
const ti = args.indexOf("--text");
if (ti !== -1 && args[ti + 1]) {
  text = args[ti + 1];
} else if (args[1] && fs.existsSync(args[1])) {
  text = fs.readFileSync(args[1], "utf8");
}
if (!text.trim()) {
  console.error("Aucun texte fourni (fichier .txt introuvable ou --text vide).");
  process.exit(1);
}

// ---- charge la géométrie du panneau --------------------------------------
const concept = path.basename(conceptDir);
const panelJson = path.join(conceptDir, `${concept}_panel.json`);
const basePng = path.join(conceptDir, "cover_paperback_base.png");
for (const f of [panelJson, basePng]) {
  if (!fs.existsSync(f)) {
    console.error(`Fichier requis introuvable : ${f}`);
    process.exit(1);
  }
}
const meta = JSON.parse(fs.readFileSync(panelJson, "utf8"));
const [px0, py0, px1, py1] = meta.panel_px;
const [tr, tg, tb] = meta.text_color;
const dpi = meta.dpi || 300;
const pad = Math.round((6 / 25.4) * dpi); // 6 mm
const maxW = px1 - px0 - 2 * pad;
const maxH = py1 - py0 - 2 * pad;

// ---- mise en lignes + dimensionnement ------------------------------------
function escapeXml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// approx largeur moyenne d'un glyphe pour une sans condensée ≈ 0.5×taille
function wrapText(str, fontPx) {
  const charW = fontPx * 0.5;
  const perLine = Math.max(8, Math.floor(maxW / charW));
  const out = [];
  for (const para of str.split("\n")) {
    if (!para.trim()) { out.push(""); continue; }
    const words = para.trim().split(/\s+/);
    let cur = "";
    for (const w of words) {
      if ((cur + " " + w).trim().length <= perLine) cur = (cur + " " + w).trim();
      else { if (cur) out.push(cur); cur = w; }
    }
    if (cur) out.push(cur);
  }
  return out;
}

const minPx = Math.round((9 / 72) * dpi); // 9 pt plancher
let fontPx = Math.round((13 / 72) * dpi);
let lines = [];
while (fontPx >= minPx) {
  lines = wrapText(text, fontPx);
  const lh = Math.round(fontPx * 1.3);
  if (lines.length * lh <= maxH) break;
  fontPx -= 2;
}
const lh = Math.round(fontPx * 1.3);

// ---- SVG du bloc texte ----------------------------------------------------
const color = `rgb(${tr},${tg},${tb})`;
let tspans = "";
let y = fontPx; // baseline première ligne
for (const ln of lines) {
  tspans += `<tspan x="${pad}" y="${y}">${escapeXml(ln)}</tspan>`;
  y += lh;
}
const svgW = px1 - px0;
const svgH = py1 - py0;
const svg = `<svg width="${svgW}" height="${svgH}" xmlns="http://www.w3.org/2000/svg">
  <style>text{font-family:'DejaVu Sans','Helvetica',sans-serif;font-size:${fontPx}px;fill:${color};}</style>
  <text>${tspans}</text>
</svg>`;

// ---- composite sur le wrap -----------------------------------------------
const outPng = path.join(conceptDir, "cover_paperback_texte.png");
sharp(basePng)
  .composite([{ input: Buffer.from(svg), left: px0, top: py0 }])
  .png()
  .toFile(outPng)
  .then(() => {
    console.log(`OK → ${outPng}  (corps ${(fontPx / dpi * 72).toFixed(1)} pt, ${lines.length} lignes)`);
    console.log("Pour le PDF KDP final avec ce texte, vois la commande Python en tête de ce fichier.");
  })
  .catch((err) => {
    console.error("Échec sharp:", err.message);
    process.exit(1);
  });
