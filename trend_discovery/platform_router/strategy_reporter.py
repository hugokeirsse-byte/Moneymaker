"""
Module 02 — Générateur de Rapport Stratégique.

Produit un rapport Markdown lisible et un export JSON à partir des
recommandations stratégiques du Module 02.

⚠️ HONNÊTETÉ DES DONNÉES :
Le rapport rappelle explicitement que les scores de compatibilité par plateforme
sont des SCORES STRUCTURELS (basés sur les profils de plateformes), tandis que la
demande/concurrence proviennent des données réelles du Module 01.
"""
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, List

from trend_discovery.platform_router.allocator import StrategicRecommendation
from trend_discovery.platform_router.platform_profiles import PLATFORM_PROFILES

logger = logging.getLogger(__name__)


class StrategyReporter:
    """Génère des rapports stratégiques Markdown + JSON pour le Module 02."""

    _PRIORITY_BADGE = {
        "immédiate": "🔥 IMMÉDIATE",
        "haute": "🟢 Haute",
        "moyenne": "🟡 Moyenne",
        "basse": "⚪ Basse",
    }

    def _platform_name(self, key: str) -> str:
        profile = PLATFORM_PROFILES.get(key)
        return profile.name if profile else key

    def _score_bar(self, score: float, width: int = 15) -> str:
        """Barre de progression ASCII pour un score 0-100."""
        filled = int(round((max(0.0, min(100.0, score)) / 100) * width))
        return f"[{'█' * filled}{'░' * (width - filled)}] {score:.0f}"

    # ── Markdown ──────────────────────────────────────────────────────────────
    def generate_markdown(self, recommendations: List[StrategicRecommendation]) -> str:
        """
        Génère le rapport stratégique complet en Markdown (français).
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines: List[str] = []

        lines.append("# 🎯 Rapport Stratégique d'Allocation Multi-Plateformes (Module 02)")
        lines.append("")
        lines.append(f"> Généré le {now} | {len(recommendations)} opportunité(s) analysée(s)")
        lines.append("")
        lines.append(
            "> ⚠️ **Note méthodologique** : les *scores de compatibilité par plateforme* "
            "sont des **scores structurels** dérivés des profils de plateformes "
            "(types de produits, public, styles qui fonctionnent). La *demande* et la "
            "*concurrence* proviennent des **données réelles** du Module 01. "
            "Les tiers de revenu sont **qualitatifs**, pas des montants."
        )
        lines.append("")

        # Tableau de synthèse / priorisation
        lines.append("---")
        lines.append("## 📋 Synthèse — Priorisation")
        lines.append("")
        lines.append("| # | Niche | Priorité | Score priorité | Score global (M01) | Top plateforme |")
        lines.append("|---|-------|----------|----------------|--------------------|----------------|")
        for i, reco in enumerate(recommendations, 1):
            badge = self._PRIORITY_BADGE.get(reco.publication_priority, reco.publication_priority)
            top = self._platform_name(reco.top_platforms[0]) if reco.top_platforms else "—"
            lines.append(
                f"| {i} | {reco.niche} | {badge} | {reco.priority_score:.0f}/100 | "
                f"{reco.global_score:.0f}/100 | {top} |"
            )
        lines.append("")

        # Détail par niche
        for i, reco in enumerate(recommendations, 1):
            badge = self._PRIORITY_BADGE.get(reco.publication_priority, reco.publication_priority)
            lines.append("---")
            lines.append(f"## {i}. {reco.niche}")
            lines.append("")
            lines.append(f"**Priorité de publication :** {badge} — {reco.priority_score:.0f}/100")
            lines.append(f"**Score global (Module 01) :** {reco.global_score:.0f}/100")
            lines.append("")
            lines.append(f"> {reco.strategy_summary}")
            lines.append("")

            # Tableau des scores par plateforme
            lines.append("### Compatibilité par plateforme (scores structurels)")
            lines.append("")
            lines.append("| Plateforme | Catégorie | Compatibilité |")
            lines.append("|------------|-----------|---------------|")
            for pkey, score in reco.platform_scores.items():
                profile = PLATFORM_PROFILES.get(pkey)
                cat = profile.category if profile else "?"
                name = profile.name if profile else pkey
                lines.append(f"| {name} | {cat} | {self._score_bar(score)} |")
            lines.append("")

            # Produits recommandés / déconseillés
            lines.append("### Produits par plateforme cible")
            lines.append("")
            for pkey in reco.top_platforms:
                name = self._platform_name(pkey)
                rec = reco.recommended_products.get(pkey, [])
                disc = reco.discouraged_products.get(pkey, [])
                lines.append(f"- **{name}**")
                lines.append(f"  - ✅ Recommandés : {', '.join(rec) if rec else '—'}")
                if disc:
                    lines.append(f"  - ❌ À éviter : {', '.join(disc)}")
            lines.append("")

            # Formats à produire
            lines.append("### Formats de contenu à produire")
            lines.append("")
            for fmt in reco.content_formats_to_produce:
                lines.append(f"- {fmt}")
            lines.append("")

            # Potentiel économique
            eco = reco.economic_potential
            lines.append("### Potentiel économique (estimation structurelle)")
            lines.append("")
            lines.append(f"- **Tier de revenu estimé :** {eco.estimated_revenue_tier}")
            lines.append(f"- **Potentiel de ventes :** {self._score_bar(eco.sales_potential)} (données réelles M01)")
            lines.append(f"- **Pression concurrentielle :** {self._score_bar(eco.competition_pressure)} (données réelles M01)")
            lines.append(f"- **Réutilisabilité :** {self._score_bar(eco.reusability_score)} (structurel)")
            lines.append(f"- **Marchés exploitables (compat ≥ 60) :** {eco.exploitable_markets_count}")
            if eco.notes:
                lines.append(f"- _{eco.notes}_")
            lines.append("")

        lines.append("---")
        lines.append("_Rapport généré par le Module 02 — Moteur d'Allocation d'Opportunités._")
        lines.append("")
        return "\n".join(lines)

    # ── Sauvegarde ──────────────────────────────────────────────────────────────
    def _to_serializable(self, reco: StrategicRecommendation) -> Dict:
        """Convertit une recommandation en dict JSON-sérialisable."""
        data = asdict(reco)
        return data

    def save_report(
        self,
        recommendations: List[StrategicRecommendation],
        output_dir: str = "./reports",
    ) -> Dict[str, str]:
        """
        Sauvegarde le rapport Markdown + JSON avec timestamp, et met à jour
        latest_strategy.md / latest_strategy.json.

        Returns:
            Dict des chemins écrits (clés: markdown, json, latest_markdown,
            latest_json). Ne lève jamais d'exception.
        """
        written: Dict[str, str] = {}
        try:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            markdown = self.generate_markdown(recommendations)
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(recommendations),
                "methodology_note": (
                    "Les scores de compatibilité par plateforme sont structurels "
                    "(basés sur les profils de plateformes). La demande et la "
                    "concurrence proviennent des données réelles du Module 01."
                ),
                "recommendations": [self._to_serializable(r) for r in recommendations],
            }

            md_path = os.path.join(output_dir, f"strategy_{timestamp}.md")
            json_path = os.path.join(output_dir, f"strategy_{timestamp}.json")
            latest_md = os.path.join(output_dir, "latest_strategy.md")
            latest_json = os.path.join(output_dir, "latest_strategy.json")

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            with open(latest_md, "w", encoding="utf-8") as f:
                f.write(markdown)
            with open(latest_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            written = {
                "markdown": md_path,
                "json": json_path,
                "latest_markdown": latest_md,
                "latest_json": latest_json,
            }
            logger.info("Rapport stratégique sauvegardé : %s", md_path)

        except Exception as exc:  # robustesse
            logger.error("Erreur StrategyReporter.save_report: %s", exc)

        return written
