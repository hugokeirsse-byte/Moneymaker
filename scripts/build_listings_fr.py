#!/usr/bin/env python3
"""
build_listings_fr.py — métadonnées françaises (titre, description, mots-clés)
pour chaque image de produits/, en CSV par dossier thématique.

Stratégie scaling : chaque série a un SOCLE de mots-clés communs (mutualisation
SEO, upload en masse) + 3-6 tags spécifiques par image. Aucune marque déposée
(ni FIFA, ni « Coupe du Monde », ni noms de clubs) dans les tags.

Usage : python scripts/build_listings_fr.py [ref]   (lit l'arborescence
produits/ du commit `ref` (défaut HEAD) via git ls-tree, écrit
produits/<theme>/listings_fr.csv)
"""
import csv
import os
import subprocess
import sys

COUNTRY_FR = {
    "france": ("France", ["bleus", "tricolore", "équipe de France"]),
    "england": ("Angleterre", ["three lions", "croix de saint georges", "équipe d'Angleterre"]),
    "spain": ("Espagne", ["la roja", "espagnol", "équipe d'Espagne"]),
    "germany": ("Allemagne", ["mannschaft", "allemand", "équipe d'Allemagne"]),
    "portugal": ("Portugal", ["seleção", "portugais", "équipe du Portugal"]),
    "netherlands": ("Pays-Bas", ["oranje", "néerlandais", "hollande"]),
    "belgium": ("Belgique", ["diables rouges", "belge", "équipe de Belgique"]),
    "switzerland": ("Suisse", ["nati", "suisse", "croix blanche"]),
    "croatia": ("Croatie", ["vatreni", "croate", "damier"]),
    "austria": ("Autriche", ["autrichien", "équipe d'Autriche"]),
    "turkey": ("Türkiye", ["turc", "croissant étoile", "équipe de Turquie"]),
    "norway": ("Norvège", ["norvégien", "croix scandinave"]),
    "scotland": ("Écosse", ["écossais", "sautoir", "chardon"]),
    "sweden": ("Suède", ["suédois", "croix scandinave"]),
    "czechia": ("Tchéquie", ["tchèque", "république tchèque"]),
    "bosnia": ("Bosnie", ["bosnien", "balkans"]),
    "argentina": ("Argentine", ["albiceleste", "argentin", "soleil de mai"]),
    "brazil": ("Brésil", ["seleção", "brésilien", "auriverde"]),
    "uruguay": ("Uruguay", ["celeste", "uruguayen"]),
    "colombia": ("Colombie", ["colombien", "cafeteros"]),
    "ecuador": ("Équateur", ["équatorien", "la tri"]),
    "paraguay": ("Paraguay", ["paraguayen", "albirroja"]),
    "usa": ("États-Unis", ["américain", "usa", "stars and stripes"]),
    "canada": ("Canada", ["canadien", "feuille d'érable"]),
    "mexico": ("Mexique", ["mexicain", "el tri", "aigle"]),
    "panama": ("Panama", ["panaméen", "canaleros"]),
    "haiti": ("Haïti", ["haïtien", "grenadiers"]),
    "curacao": ("Curaçao", ["curacien", "caraïbes"]),
    "japan": ("Japon", ["japonais", "samurai blue", "soleil levant"]),
    "south_korea": ("Corée du Sud", ["coréen", "taeguk", "guerriers taeguk"]),
    "australia": ("Australie", ["australien", "socceroos", "croix du sud"]),
    "iran": ("Iran", ["iranien", "team melli"]),
    "saudi_arabia": ("Arabie Saoudite", ["saoudien", "faucons verts"]),
    "qatar": ("Qatar", ["qatari", "maroon"]),
    "iraq": ("Irak", ["irakien", "lions de mésopotamie"]),
    "jordan": ("Jordanie", ["jordanien", "nashama"]),
    "uzbekistan": ("Ouzbékistan", ["ouzbek", "loups blancs"]),
    "new_zealand": ("Nouvelle-Zélande", ["néo-zélandais", "all whites", "croix du sud"]),
    "morocco": ("Maroc", ["marocain", "lions de l'atlas", "étoile verte"]),
    "senegal": ("Sénégal", ["sénégalais", "lions de la teranga"]),
    "ivory_coast": ("Côte d'Ivoire", ["ivoirien", "éléphants"]),
    "algeria": ("Algérie", ["algérien", "fennecs", "croissant"]),
    "tunisia": ("Tunisie", ["tunisien", "aigles de carthage"]),
    "egypt": ("Égypte", ["égyptien", "pharaons"]),
    "ghana": ("Ghana", ["ghanéen", "black stars", "étoile noire"]),
    "south_africa": ("Afrique du Sud", ["sud-africain", "bafana bafana"]),
    "cape_verde": ("Cap-Vert", ["capverdien", "requins bleus"]),
    "congo_dr": ("RD Congo", ["congolais", "léopards"]),
}

STYLE_FR = {
    "risograph": "risographie", "flat_vector": "vectoriel", "ukiyo_e": "ukiyo-e",
    "retro_neon_80s": "néon rétro 80s", "cut_paper_collage": "collage papier",
    "vintage_watercolor": "aquarelle vintage", "cartoon_network": "cartoon",
    "victorian_engraving": "gravure victorienne", "memphis_design": "design Memphis",
    "ghibli_painted": "peinture animée", "pixel_art": "pixel art",
    "minimalist_line": "ligne minimaliste", "gothic_dark": "gothique",
    "psychedelic_60s": "psychédélique 60s", "kawaii_chibi": "kawaii",
    "woodcut_linocut": "linogravure", "tattoo_flash": "tattoo old school",
    "art_nouveau": "art nouveau", "swiss_constructivist": "constructiviste",
    "pop_art": "pop art", "embroidery_patch": "patch brodé",
}

DESIGN_FR = {
    "pride_unicorn": ("Licorne arc-en-ciel", ["licorne", "arc-en-ciel"]),
    "pride_heart_flag": ("Cœur drapeau arc-en-ciel", ["cœur", "arc-en-ciel"]),
    "pride_hands_heart": ("Mains en cœur arc-en-ciel", ["mains", "cœur", "arc-en-ciel"]),
    "juneteenth_star_sunrise": ("Étoile au lever de soleil Juneteenth", ["étoile", "lever de soleil", "liberté"]),
    "juneteenth_chains_birds": ("Chaînes brisées et oiseaux libres", ["liberté", "oiseaux", "émancipation"]),
    "juneteenth_celebration": ("Célébration Juneteenth", ["célébration", "liberté"]),
    "fathersday_pier": ("Pêche au ponton père et enfant", ["pêche", "complicité", "souvenir"]),
    "fathersday_superteam": ("Super-équipe père et enfant", ["super-héros", "complicité"]),
    "fathersday_trophy_hug": ("Câlin trophée du meilleur papa", ["trophée", "câlin", "meilleur papa"]),
    "dragonboat": ("Bateaux-dragons", ["bateau-dragon", "tradition"]),
    "fete_musique": ("Fête de la musique", ["musique", "concert", "été"]),
    "midsommar": ("Midsommar", ["solstice", "été", "scandinave"]),
    "fathers_day": ("Complicité père et enfant", ["papa", "complicité"]),
}

SERIES = {
    # dossier: (socle de tags communs, gabarit titre, gabarit description)
    "coupe_du_monde/drapeaux": (
        ["drapeau", "patch brodé", "écusson", "football", "foot 2026", "supporter",
         "équipe nationale", "broderie", "badge", "mondial", "fan de foot", "tournoi 2026"],
        "Écusson brodé drapeau {pays} – Football 2026",
        "Patch brodé du drapeau {pays}, rendu broderie cousue main avec liseré "
        "cordelette, fond transparent. Parfait pour supporter votre équipe pendant "
        "le tournoi 2026 : stickers, t-shirts, mugs, casquettes.",
    ),
    "coupe_du_monde/ballons": (
        ["ballon de foot", "patch brodé", "écusson", "football", "foot 2026", "supporter",
         "équipe nationale", "broderie", "badge", "mondial", "fan de foot", "drapeau"],
        "Ballon de foot drapeau {pays} – Écusson brodé 2026",
        "Ballon de football iconique dont les pentagones portent le drapeau {pays}, "
        "façon patch brodé cousu main, fond transparent. Le cadeau parfait du "
        "supporter pour le tournoi 2026.",
    ),
    "fete_des_peres/patchs": (
        ["fête des pères", "papa", "cadeau papa", "patch brodé", "écusson", "humour",
         "broderie", "badge", "cadeau fête des pères", "meilleur papa", "daddy", "père"],
        "Patch brodé {design} – Fête des Pères",
        "Écusson humoristique « {design} » façon broderie cousue main, fond "
        "transparent. Le cadeau drôle et tendre pour la fête des pères : t-shirt, "
        "mug, sticker, tablier.",
    ),
    "fete_des_peres/scenes": (
        ["fête des pères", "papa", "cadeau papa", "père et enfant", "complicité",
         "cadeau fête des pères", "illustration", "meilleur papa", "famille", "tendresse"],
        "{design} – Fête des Pères (style {style})",
        "Illustration « {design} » en style {style}, fond transparent. Une scène "
        "pleine de tendresse pour célébrer les papas : affiche, t-shirt, carte, mug.",
    ),
    "pride": (
        ["pride", "lgbt", "arc-en-ciel", "fierté", "love is love", "égalité",
         "rainbow", "mois des fiertés", "inclusif", "amour", "diversité"],
        "{design} – Pride (style {style})",
        "Design « {design} » en style {style}, fond transparent. Célébrez le mois "
        "des fiertés en couleurs : stickers, t-shirts, totes, mugs.",
    ),
    "pride/slogans": (
        ["pride", "lgbt", "arc-en-ciel", "fierté", "slogan", "patch brodé",
         "écusson", "broderie", "love is love", "égalité", "rainbow",
         "mois des fiertés", "fierté toute l'année", "inclusif", "diversité"],
        "Écusson brodé {design} – Pride toute l'année",
        "Patch brodé du slogan « {design} », broderie cousue main avec liseré "
        "cordelette, fond transparent. La fierté ne se limite pas à juin : "
        "stickers, t-shirts, vestes, totes, mugs.",
    ),
    "fete_des_peres/slogans": (
        ["fête des pères", "papa", "cadeau papa", "patch brodé", "écusson",
         "slogan", "humour", "broderie", "badge", "cadeau fête des pères",
         "meilleur papa", "daddy", "père"],
        "Écusson brodé {design} – Fête des Pères",
        "Patch brodé du slogan « {design} », broderie cousue main, fond "
        "transparent. Le cadeau drôle et tendre pour la fête des pères : "
        "t-shirt, mug, sticker, casquette.",
    ),
    "juneteenth": (
        ["juneteenth", "liberté", "émancipation", "histoire afro-américaine",
         "19 juin", "freedom day", "héritage", "fierté noire", "célébration"],
        "{design} – Juneteenth (style {style})",
        "Design « {design} » en style {style}, fond transparent, pour célébrer "
        "Juneteenth et la liberté : t-shirts, affiches, stickers.",
    ),
    "fetes_de_juin": (
        ["été", "juin", "festival", "célébration", "solstice", "tradition", "fête"],
        "{design} (style {style})",
        "Design « {design} » en style {style}, fond transparent. Un visuel de "
        "saison pour les fêtes de juin : t-shirts, affiches, stickers.",
    ),
    "humour_patchs": (
        ["patch brodé", "écusson", "humour", "broderie", "badge", "drôle",
         "cadeau humour", "jeu de mots", "sticker", "fun"],
        "Patch brodé humour – {design}",
        "Écusson humoristique « {design} » façon broderie cousue main, fond "
        "transparent. Un clin d'œil à porter partout : veste, sac, t-shirt, mug.",
    ),
    "humour_adulte": (
        ["patch brodé", "écusson", "humour adulte", "broderie", "badge", "drôle",
         "second degré", "cadeau humour", "expression", "fun"],
        "Patch brodé humour – {design}",
        "Écusson second degré « {design} » façon broderie, fond transparent. "
        "Pour ceux qui assument : veste, sac, mug, sticker.",
    ),
}


def labels_from_cdcs():
    """Récupère les libellés (_canva_text) des designs depuis les CdC JSON."""
    import glob
    import json
    labels = {}
    for f in glob.glob("reports/redbubble/cahiers_des_charges_*.json"):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for b in d.get("briefs", []):
            eid = b.get("_expression_id", "")
            txt = b.get("_canva_text") or b.get("_idiom") or ""
            if eid and txt:
                labels[eid] = txt.title()
    return labels


def list_tree(folder: str, ref: str = "HEAD"):
    """Fichiers PNG directement dans produits/<folder>/ (pas les sous-dossiers,
    chaque série a sa propre entrée ; les _sur_feutre ne sont pas des produits)."""
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", ref,
                          f"produits/{folder}/"],
                         capture_output=True, text=True).stdout.split("\0")
    prefix = f"produits/{folder}/"
    return [p for p in out if p.lower().endswith(".png")
            and os.path.dirname(p) + "/" == prefix]


def parse_name(fname: str):
    """'pride_unicorn___pop_art___base_*.png' -> (design, style) ; 'france.png' -> ('france', None)."""
    base = os.path.splitext(os.path.basename(fname))[0]
    if "___" in base:
        parts = base.split("___")
        return parts[0], parts[1]
    return base, None


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    cdc_labels = labels_from_cdcs()
    total = 0
    for folder, (common, t_title, t_desc) in SERIES.items():
        files = list_tree(folder, ref)
        if not files:
            print(f"(vide) {folder}")
            continue
        rows = []
        for path in sorted(files):
            design_id, style_id = parse_name(path)
            # les variantes portent un suffixe d'ambiance : cartoon_network__marrant_
            style_base = (style_id or "").split("__")[0]
            style_fr = STYLE_FR.get(style_base, style_base.replace("_", " "))
            if design_id in COUNTRY_FR:
                pays, extra = COUNTRY_FR[design_id]
                title = t_title.format(pays=pays)
                desc = t_desc.format(pays=pays)
                spec = [pays.lower()] + extra
            else:
                d_fr, extra = DESIGN_FR.get(design_id, (None, []))
                if d_fr is None:
                    d_fr = cdc_labels.get(design_id, design_id.replace("_", " ").title())
                if folder.endswith("/slogans"):
                    d_fr = d_fr.upper()  # les slogans sont brodés en capitales
                title = t_title.format(design=d_fr, style=style_fr)
                desc = t_desc.format(design=d_fr, style=style_fr)
                spec = [d_fr.lower()] + extra + ([style_fr] if style_fr else [])
            tags = list(dict.fromkeys(common + spec))[:25]
            rows.append({"fichier": os.path.basename(path), "titre": title,
                         "description": desc, "mots_cles": ", ".join(tags)})
        out_dir = os.path.join("produits", folder)
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, "listings_fr.csv")
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=["fichier", "titre", "description", "mots_cles"])
            w.writeheader()
            w.writerows(rows)
        print(f"{out_csv} : {len(rows)} listings")
        total += len(rows)
    print(f"\n{total} listings générés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
