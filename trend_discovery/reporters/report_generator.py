"""
Report generator — produces a structured Markdown + JSON report from all scoring data.
"""
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from trend_discovery.analyzers.feasibility_scorer import FeasibilityScore
from trend_discovery.analyzers.hybrid_scorer import HybridNiche
from trend_discovery.analyzers.trend_scorer import TrendScore

logger = logging.getLogger(__name__)


@dataclass
class NicheReport:
    generated_at: str = ""
    sources_consulted: List[str] = field(default_factory=list)
    keywords_analyzed: int = 0
    top_niches: List[TrendScore] = field(default_factory=list)
    top_hybrids: List[HybridNiche] = field(default_factory=list)
    feasibility_scores: List[FeasibilityScore] = field(default_factory=list)
    competition_data: Dict = field(default_factory=dict)
    execution_time_seconds: float = 0.0


class ReportGenerator:
    """Generates human-readable Markdown and machine-readable JSON reports."""

    def _score_bar(self, score: float, width: int = 20) -> str:
        """ASCII progress bar for a 0-100 score."""
        filled = int((score / 100) * width)
        return f"[{'█' * filled}{'░' * (width - filled)}] {score:.1f}/100"

    def _competition_label(self, score: float) -> str:
        if score < 35:
            return "🟢 Faible"
        elif score < 65:
            return "🟡 Moyenne"
        else:
            return "🔴 Forte"

    def _trend_arrow(self, direction: str) -> str:
        return {"rising": "↑ En hausse", "stable": "→ Stable", "declining": "↓ En baisse"}.get(direction, "→")

    def generate_markdown(self, report: NicheReport) -> str:
        lines = []
        lines.append(f"# 🎯 Rapport de Dénicheuse POD — {report.generated_at[:10]}")
        lines.append("")
        lines.append(f"> Généré le {report.generated_at} | {report.keywords_analyzed} mots-clés analysés")
        lines.append(f"> Sources : {', '.join(report.sources_consulted) or 'N/A'}")
        lines.append("")

        # --- RÉSUMÉ EXÉCUTIF ---
        lines.append("---")
        lines.append("## 📊 Résumé Exécutif")
        lines.append("")
        if report.top_niches:
            lines.append("### 🏆 Top 5 Niches Recommandées")
            lines.append("")
            lines.append("| Rang | Niche | Score Trend | Direction | Faisabilité |")
            lines.append("|------|-------|-------------|-----------|-------------|")
            feasibility_map = {f.niche: f for f in report.feasibility_scores}
            for i, ts in enumerate(report.top_niches[:5], 1):
                feas = feasibility_map.get(ts.keyword)
                feas_score = f"{feas.overall_feasibility:.0f}/100" if feas else "N/A"
                lines.append(
                    f"| {i} | **{ts.keyword}** | {ts.overall_trend_score:.1f}/100 "
                    f"| {self._trend_arrow(ts.trend_direction)} | {feas_score} |"
                )
            lines.append("")

        if report.top_hybrids:
            lines.append("### 🔀 Top 3 Niches Hybrides")
            lines.append("")
            for h in report.top_hybrids[:3]:
                lines.append(f"- **{h.niche1} × {h.niche2}** — Score hybride : {h.hybrid_score:.1f}/100")
            lines.append("")

        # --- ANALYSE PAR NICHE ---
        lines.append("---")
        lines.append("## 🔍 Analyse Détaillée par Niche")
        lines.append("")
        feasibility_map = {f.niche: f for f in report.feasibility_scores}
        comp_data = report.competition_data

        for ts in report.top_niches[:15]:
            feas = feasibility_map.get(ts.keyword)
            comp = comp_data.get(ts.keyword, {})
            comp_score = comp.get("competition_score", 50.0)
            opp_score = comp.get("opportunity_score", 50.0)

            lines.append(f"### `{ts.keyword.upper()}`")
            lines.append("")
            lines.append(f"**Score Global de Trend :** {self._score_bar(ts.overall_trend_score)}")
            lines.append("")
            lines.append("| Indicateur | Score | Détail |")
            lines.append("|-----------|-------|--------|")
            lines.append(f"| 📈 Trend Google | {ts.google_trend_score:.1f}/100 | {self._trend_arrow(ts.trend_direction)} (vélocité: {ts.trend_velocity:+.1f}) |")
            lines.append(f"| 💬 Buzz Reddit | {ts.reddit_buzz_score:.1f}/100 | Mentions dans communautés POD |")
            lines.append(f"| 🔍 Volume de Recherche | {ts.search_volume_proxy:.1f}/100 | Proxy autocomplete Google |")
            lines.append(f"| 🌊 Saisonnalité | {ts.seasonality_score:.1f}/100 | {'Forte saisonnalité' if ts.seasonality_score > 50 else 'Peu saisonnière'} |")
            lines.append(f"| ⚔️ Compétition RB | {comp_score:.1f}/100 | {self._competition_label(comp_score)} ({comp.get('result_count', '?')} résultats) |")
            lines.append(f"| 💡 Opportunité | {opp_score:.1f}/100 | {'🟢 Forte opportunité' if opp_score > 60 else '🟡 Opportunité modérée'} |")

            if feas:
                lines.append(f"| 🤖 Faisabilité IA | {feas.overall_feasibility:.1f}/100 | Facilité de génération d'images |")
                lines.append(f"| 🧩 Compatibilité Seamless | {feas.seamless_compatibility:.1f}/100 | Adapté aux patterns répétitifs |")
                lines.append(f"| 🎨 Flexibilité Couleurs | {feas.color_flexibility:.1f}/100 | Déclinable facilement |")

            lines.append("")
            if feas and feas.prompt_suggestions:
                lines.append("**💬 Prompts AI suggérés :**")
                lines.append("")
                for prompt in feas.prompt_suggestions[:2]:
                    lines.append(f"> {prompt}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # --- NICHES HYBRIDES ---
        lines.append("## 🔀 Niches Hybrides Recommandées")
        lines.append("")
        lines.append(
            "Les combinaisons hybrides offrent moins de compétition directe et "
            "permettent de cibler des micro-communautés très engagées."
        )
        lines.append("")

        for h in report.top_hybrids[:10]:
            lines.append(f"### `{h.niche1.upper()} × {h.niche2.upper()}`")
            lines.append("")
            lines.append(f"**Score Hybride :** {self._score_bar(h.hybrid_score)}")
            lines.append("")
            lines.append("| Composante | Score |")
            lines.append("|-----------|-------|")
            lines.append(f"| 📈 Trend moyen des 2 niches | {h.trend_score:.1f}/100 |")
            lines.append(f"| 🎯 Unicité (faible compétition) | {h.uniqueness_score:.1f}/100 |")
            lines.append(f"| 🤝 Synergie visuelle | {h.synergy_score:.1f}/100 |")
            lines.append("")
            lines.append("**Exemples de produits :**")
            for ex in h.example_products:
                lines.append(f"- {ex}")
            lines.append("")

        # --- CAHIER DES CHARGES TOP 3 ---
        lines.append("---")
        lines.append("## 📋 Cahier des Charges — Top 3 Niches Prioritaires")
        lines.append("")

        feasibility_map = {f.niche: f for f in report.feasibility_scores}
        for rank, ts in enumerate(report.top_niches[:3], 1):
            feas = feasibility_map.get(ts.keyword)
            comp = comp_data.get(ts.keyword, {})
            lines.append(f"### #{rank} — {ts.keyword.title()}")
            lines.append("")
            lines.append(f"**Priorité :** {'🔥 HAUTE' if ts.overall_trend_score > 60 else '⭐ MOYENNE'}")
            lines.append("")
            lines.append("#### Objectif")
            lines.append(
                f"Créer une collection de patterns seamless sur la niche **{ts.keyword}** "
                f"pour Spoonflower et RedBubble."
            )
            lines.append("")
            lines.append("#### Spécifications Techniques")
            lines.append("- Format : PNG 150 DPI minimum, 3600×3600px")
            lines.append("- Style : Seamless/repeat pattern")
            lines.append("- Variantes de couleurs : 3 minimum par design")
            lines.append("- Nommage : `{niche}_{style}_{colorway}_{version}.png`")
            lines.append("")
            lines.append("#### Prompts de Production")
            if feas:
                for p in feas.prompt_suggestions:
                    lines.append(f"```\n{p}\n```")
            lines.append("")
            lines.append("#### Plateformes Cibles")
            lines.append("1. **Spoonflower** — fabric, wallpaper, gift wrap")
            lines.append("2. **RedBubble** — stickers, phone cases, tote bags, leggings")
            lines.append("")
            lines.append("#### Score de Faisabilité Globale")
            overall = ((ts.overall_trend_score + (feas.overall_feasibility if feas else 70)) / 2)
            lines.append(f"{self._score_bar(overall)}")
            lines.append("")

        # --- MÉTHODOLOGIE ---
        lines.append("---")
        lines.append("## 🔬 Méthodologie & Sources")
        lines.append("")
        lines.append("| Source | Type | API Key requise | Fiabilité |")
        lines.append("|--------|------|-----------------|-----------|")
        lines.append("| Google Trends (pytrends) | Tendances de recherche | ❌ Non | ⭐⭐⭐⭐ |")
        lines.append("| Google Autocomplete | Volume de recherche proxy | ❌ Non | ⭐⭐⭐ |")
        lines.append("| Reddit (API publique) | Buzz communautaire | ❌ Non | ⭐⭐⭐ |")
        lines.append("| Spoonflower (scraping) | Compétition plateforme | ❌ Non | ⭐⭐⭐⭐ |")
        lines.append("| RedBubble (scraping) | Compétition plateforme | ❌ Non | ⭐⭐⭐⭐ |")
        lines.append("")
        lines.append("### Formule de Score Global")
        lines.append("```")
        lines.append("Score Niche = (Google Trend × 30%) + (Reddit Buzz × 20%)")
        lines.append("           + (Opportunité Compétition × 20%) + (Faisabilité × 15%)")
        lines.append("           + (Anti-saisonnalité × 15%)")
        lines.append("")
        lines.append("Score Hybride = (Trend Moyen × 40%) + (Unicité × 35%) + (Synergie Visuelle × 25%)")
        lines.append("```")
        lines.append("")
        lines.append(f"*Rapport généré automatiquement par le système Moneymaker — {report.generated_at}*")

        return "\n".join(lines)

    def generate_json(self, report: NicheReport) -> str:
        """Serialize the full report to JSON."""
        def convert(obj):
            if hasattr(obj, "__dataclass_fields__"):
                return asdict(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        data = {
            "generated_at": report.generated_at,
            "sources_consulted": report.sources_consulted,
            "keywords_analyzed": report.keywords_analyzed,
            "execution_time_seconds": report.execution_time_seconds,
            "top_niches": [asdict(t) for t in report.top_niches],
            "top_hybrids": [asdict(h) for h in report.top_hybrids],
            "feasibility_scores": [asdict(f) for f in report.feasibility_scores],
            "competition_data": report.competition_data,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def save_report(self, report: NicheReport, output_dir: str = "./reports") -> Dict[str, str]:
        """
        Save both Markdown and JSON versions of the report.

        Returns:
            {"markdown": path, "json": path}
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        md_path = os.path.join(output_dir, f"trend_report_{timestamp}.md")
        json_path = os.path.join(output_dir, f"trend_report_{timestamp}.json")

        md_content = self.generate_markdown(report)
        json_content = self.generate_json(report)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)

        # Also write/overwrite a "latest" symlink-style file
        latest_md = os.path.join(output_dir, "latest_report.md")
        latest_json = os.path.join(output_dir, "latest_report.json")
        with open(latest_md, "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(latest_json, "w", encoding="utf-8") as f:
            f.write(json_content)

        logger.info("Reports saved: %s, %s", md_path, json_path)
        return {"markdown": md_path, "json": json_path}
