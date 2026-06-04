"""
ApprovalGate — Garde-fou dépenses avant génération d'images Runware.

Règle : aucune image générée sans approbation explicite de chaque CdC.
Chaque CdC approuvée → exactement N images (défaut: 5).

Flux :
1. preview → génère CdCs + écrit data/approvals/pending_TIMESTAMP.json
2. L'utilisateur édite le manifest (approved: true pour les CdCs choisies)
3. generate → lit le manifest, génère seulement les CdCs approuvées
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from trend_discovery.generators.production_brief import ProductionBrief

logger = logging.getLogger(__name__)

RUNWARE_PRICE_PER_IMAGE_EUR = 0.006  # ~0.006€/image (1024×1024)
DEFAULT_IMAGES_PER_BRIEF = 5


@dataclass
class BriefApproval:
    niche_name: str
    opportunity_score: float
    approved: bool = False
    images_count: int = DEFAULT_IMAGES_PER_BRIEF


class ApprovalGate:
    def __init__(self, manifest_dir: str = "data/approvals"):
        self.manifest_dir = manifest_dir

    def write_pending_manifest(self, briefs: List["ProductionBrief"], run_id: str) -> str:
        """
        Écrit le manifest d'approbation après génération des CdCs.
        Returns the manifest file path.
        """
        os.makedirs(self.manifest_dir, exist_ok=True)

        entries = []
        for b in briefs:
            entries.append({
                "niche_name": b.name,
                "opportunity_score": round(b.opportunity_score, 1),
                "confidence": round(b.confidence, 1),
                "positive_prompt_preview": (b.positive_prompt or "")[:100],
                "approved": False,
                "images_count": DEFAULT_IMAGES_PER_BRIEF,
            })

        manifest = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "instructions": (
                "Set 'approved': true for each CdC you want to generate. "
                "Each approved CdC will generate exactly 'images_count' images."
            ),
            "briefs": entries,
        }

        path = os.path.join(self.manifest_dir, f"pending_{run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        logger.info(
            "[ApprovalGate] manifest écrit: %s\n"
            "  → Éditez 'approved': true pour les CdCs choisies, puis lancez 'generate'.",
            path,
        )
        return path

    def load_approved(self, manifest_path: str) -> List[BriefApproval]:
        """
        Lit le manifest, retourne seulement les BriefApproval avec approved=true.
        Raise ValueError si aucun CdC approuvé.
        """
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        approved = []
        for entry in data.get("briefs", []):
            if entry.get("approved"):
                approved.append(BriefApproval(
                    niche_name=entry["niche_name"],
                    opportunity_score=float(entry.get("opportunity_score", 0.0)),
                    approved=True,
                    images_count=int(entry.get("images_count", DEFAULT_IMAGES_PER_BRIEF)),
                ))

        if not approved:
            raise ValueError(
                f"Aucun CdC approuvé dans {manifest_path}. "
                "Éditez le manifest et mettez 'approved': true sur les niches choisies."
            )

        return approved

    def estimate_cost(self, approvals: List[BriefApproval]) -> Dict:
        """Returns {n_images, cost_eur, breakdown}"""
        breakdown = []
        total_images = 0
        for a in approvals:
            n = a.images_count
            cost = n * RUNWARE_PRICE_PER_IMAGE_EUR
            total_images += n
            breakdown.append({
                "niche_name": a.niche_name,
                "images": n,
                "cost_eur": round(cost, 4),
            })
        return {
            "n_images": total_images,
            "cost_eur": round(total_images * RUNWARE_PRICE_PER_IMAGE_EUR, 4),
            "breakdown": breakdown,
        }

    def find_latest_manifest(self) -> Optional[str]:
        """Trouve le manifest le plus récent dans manifest_dir."""
        if not os.path.isdir(self.manifest_dir):
            return None

        candidates = [
            os.path.join(self.manifest_dir, f)
            for f in os.listdir(self.manifest_dir)
            if f.startswith("pending_") and f.endswith(".json")
        ]
        if not candidates:
            return None

        return max(candidates, key=os.path.getmtime)
