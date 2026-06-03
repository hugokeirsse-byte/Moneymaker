"""
Phase 3 — Construction des Arbres de Niches.

Décompose automatiquement chaque sujet en arbre hiérarchique :
  Botanique
  ├── Flore sauvage
  ├── Plantes médicinales
  │   ├── Herboristerie
  │   └── Apothicaire
  ├── Botanique victorienne
  └── Herbier historique

Chaque nœud devient une niche potentielle.
Chaque sous-nœud devient une sous-niche potentielle.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NicheNode:
    name: str
    parent: Optional[str] = None
    level: int = 0
    keywords: List[str] = field(default_factory=list)  # search terms for this node
    children: List[str] = field(default_factory=list)   # child node names


# ─────────────────────────────────────────────────────────────────────────────
# Ontologie POD complète — arbre de niches statique
# ─────────────────────────────────────────────────────────────────────────────
_RAW_TREE: Dict = {
    "Nature & Botanique": {
        "_keywords": ["botanical pattern", "nature design", "plant pattern"],
        "Floral": {
            "_keywords": ["floral pattern", "flower design", "fleurs"],
            "Roses & Pivoines": {"_keywords": ["roses pattern", "peonies", "rosa"]},
            "Fleurs Sauvages": {"_keywords": ["wildflowers", "meadow flowers", "prairie"]},
            "Ditsy Floral": {"_keywords": ["ditsy floral", "small flowers pattern", "tiny flowers"]},
            "Fleurs Tropicales": {"_keywords": ["tropical flowers", "hibiscus", "bird of paradise"]},
        },
        "Botanique": {
            "_keywords": ["botanical illustration", "botanica", "plant illustration"],
            "Botanique Victorienne": {"_keywords": ["victorian botanical", "antique botanical", "vintage botanical print"]},
            "Botanique Scientifique": {"_keywords": ["scientific illustration", "natural history print", "herbarium"]},
            "Fougères & Mousses": {"_keywords": ["fern pattern", "moss", "ferns", "forest floor"]},
            "Succulentes": {"_keywords": ["succulent pattern", "cactus", "desert plants"]},
        },
        "Herboristerie": {
            "_keywords": ["herbal pattern", "herbs", "medicinal plants"],
            "Apothicaire": {"_keywords": ["apothecary", "apothecary bottles", "potion herbs"]},
            "Jardin de Sorcière": {"_keywords": ["witch garden", "witch herbs", "magical plants"]},
            "Plantes Médicinales Médiévales": {"_keywords": ["medieval herbs", "medieval medicine", "illuminated manuscript plants"]},
            "Cuisine Aromatique": {"_keywords": ["kitchen herbs", "cooking herbs", "culinary plants"]},
        },
        "Champignons": {
            "_keywords": ["mushroom pattern", "fungi", "toadstool"],
            "Champignons Sauvages": {"_keywords": ["wild mushrooms", "forest mushrooms", "amanita"]},
            "Champignons Mignons": {"_keywords": ["cute mushrooms", "kawaii mushroom", "cartoon mushroom"]},
            "Champignons Psychédéliques": {"_keywords": ["psychedelic mushroom", "magic mushroom art", "trippy fungi"]},
        },
        "Forêt & Bois": {
            "_keywords": ["forest pattern", "woodland", "trees design"],
            "Forêt Enchantée": {"_keywords": ["enchanted forest", "magical forest", "fairy forest"]},
            "Bois Sombres": {"_keywords": ["dark forest", "moody forest", "gothic forest"]},
            "Forêt Boréale": {"_keywords": ["boreal forest", "pine forest", "nordic forest", "taiga"]},
        },
        "Océan & Marin": {
            "_keywords": ["ocean pattern", "marine design", "sea pattern"],
            "Fond Marin": {"_keywords": ["underwater pattern", "coral reef", "deep sea"]},
            "Côtier & Plage": {"_keywords": ["coastal pattern", "beach design", "nautical"]},
            "Créatures Marines": {"_keywords": ["sea creatures", "jellyfish", "seahorse pattern"]},
        },
        "Tropical": {
            "_keywords": ["tropical pattern", "jungle design", "tropics"],
            "Feuilles Tropicales": {"_keywords": ["tropical leaves", "palm leaf", "monstera pattern"]},
            "Oiseaux Tropicaux": {"_keywords": ["tropical birds", "parrot pattern", "toucan"]},
        },
    },
    "Animaux": {
        "_keywords": ["animal pattern", "wildlife design", "creature pattern"],
        "Chats": {
            "_keywords": ["cat pattern", "cats design", "feline"],
            "Chats Mignons": {"_keywords": ["cute cats", "kawaii cats", "cartoon cats"]},
            "Chats Réalistes": {"_keywords": ["realistic cat", "watercolor cat", "cat portrait"]},
            "Chats Mystiques": {"_keywords": ["black cat", "witch cat", "mystical cat", "celestial cat"]},
        },
        "Chiens": {
            "_keywords": ["dog pattern", "dogs design", "canine"],
            "Chiens de Race": {"_keywords": ["dachshund pattern", "corgi pattern", "breed specific"]},
        },
        "Animaux des Bois": {
            "_keywords": ["woodland animals", "forest creatures", "woodland critters"],
            "Renards": {"_keywords": ["fox pattern", "foxes design", "woodland fox"]},
            "Cerfs & Biches": {"_keywords": ["deer pattern", "stag design", "forest deer"]},
            "Lapins": {"_keywords": ["rabbit pattern", "bunny design", "hare"]},
            "Hérissons": {"_keywords": ["hedgehog pattern", "hedgehog design"]},
            "Écureuils": {"_keywords": ["squirrel pattern", "squirrel design"]},
        },
        "Oiseaux": {
            "_keywords": ["bird pattern", "birds design", "avian"],
            "Corbeaux & Corneilles": {"_keywords": ["raven pattern", "crow design", "dark birds"]},
            "Chouettes & Hiboux": {"_keywords": ["owl pattern", "owl design", "owl art"]},
            "Oiseaux Chanteurs": {"_keywords": ["songbird pattern", "garden birds", "robin wren"]},
        },
        "Insectes": {
            "_keywords": ["insect pattern", "bugs design", "entomology"],
            "Papillons": {"_keywords": ["butterfly pattern", "butterfly design", "lepidoptera"]},
            "Mites & Sphinx": {"_keywords": ["moth pattern", "hawk moth", "luna moth"]},
            "Abeilles": {"_keywords": ["bee pattern", "honeybee design", "bumblebee"]},
            "Coléoptères": {"_keywords": ["beetle pattern", "bug art", "scarab"]},
        },
        "Animaux Fantastiques": {
            "_keywords": ["mythical animals", "fantasy creatures", "magical beasts"],
            "Licornes": {"_keywords": ["unicorn pattern", "unicorn design", "rainbow unicorn"]},
            "Dragons": {"_keywords": ["dragon pattern", "dragon design", "serpent dragon"]},
        },
    },
    "Styles Esthétiques": {
        "_keywords": ["aesthetic pattern", "style design", "trend aesthetic"],
        "Cottagecore": {
            "_keywords": ["cottagecore pattern", "cottage aesthetic", "rural charm"],
            "Cottagecore Romantique": {"_keywords": ["romantic cottage", "english cottage garden", "cottage roses"]},
            "Cottagecore Automnal": {"_keywords": ["autumn cottagecore", "fall cottagecore", "harvest cottage"]},
        },
        "Dark Academia": {
            "_keywords": ["dark academia", "academic aesthetic", "gothic scholarly"],
            "Dark Academia Botanique": {"_keywords": ["dark botanical", "moody botanical", "gothic plant"]},
        },
        "Goblincore": {
            "_keywords": ["goblincore", "goblin aesthetic", "frogcore"],
            "Goblincore Champignons": {"_keywords": ["goblin mushrooms", "mushroom hoard", "forest goblin"]},
        },
        "Fairycore": {
            "_keywords": ["fairycore", "fairy aesthetic", "fae garden"],
            "Fairy Cottagecore": {"_keywords": ["fairy cottage", "enchanted garden", "flower fairy"]},
        },
        "Witchy & Occulte": {
            "_keywords": ["witchy aesthetic", "occult design", "magic pattern"],
            "Witchy Moderne": {"_keywords": ["modern witch", "hedge witch", "kitchen witch"]},
            "Witchy Gothique": {"_keywords": ["gothic witch", "dark witch", "halloween witch"]},
        },
        "Gothique": {
            "_keywords": ["gothic pattern", "dark aesthetic", "goth design"],
            "Gothique Victorien": {"_keywords": ["victorian gothic", "mourning jewelry", "memento mori"]},
            "Gothique Romantique": {"_keywords": ["romantic gothic", "dark romance", "gothic floral"]},
        },
        "Japandi": {
            "_keywords": ["japandi design", "japanese minimalism", "wabi sabi"],
        },
        "Boho": {
            "_keywords": ["boho pattern", "bohemian design", "hippie aesthetic"],
            "Boho Géométrique": {"_keywords": ["boho geometric", "tribal geometric", "aztec"]},
            "Boho Floral": {"_keywords": ["boho floral", "bohemian flowers", "free spirit floral"]},
        },
        "Solarpunk": {
            "_keywords": ["solarpunk design", "eco punk", "green future aesthetic"],
        },
        "Cyberpunk": {
            "_keywords": ["cyberpunk pattern", "neon aesthetic", "tech dystopian"],
        },
    },
    "Styles Graphiques": {
        "_keywords": ["graphic style pattern", "design style", "pattern style"],
        "Géométrique": {
            "_keywords": ["geometric pattern", "shapes design", "tessellation"],
            "Géométrique Minimaliste": {"_keywords": ["minimal geometric", "clean shapes", "simple geometry"]},
            "Géométrique Complexe": {"_keywords": ["complex geometric", "mandala", "sacred geometry"]},
            "Géométrique Organique": {"_keywords": ["organic geometric", "soft shapes", "blob pattern"]},
        },
        "Aquarelle": {
            "_keywords": ["watercolor pattern", "painted design", "wash technique"],
            "Aquarelle Floral": {"_keywords": ["watercolor flowers", "painted flowers", "floral wash"]},
            "Aquarelle Abstrait": {"_keywords": ["abstract watercolor", "color wash", "watercolor blur"]},
        },
        "Art Nouveau": {
            "_keywords": ["art nouveau pattern", "nouveau design", "jugendstil"],
            "Art Nouveau Floral": {"_keywords": ["art nouveau flowers", "nouveau botanical", "mucha style"]},
            "Art Nouveau Animaux": {"_keywords": ["art nouveau animals", "nouveau creatures", "decorative animals"]},
        },
        "Art Déco": {
            "_keywords": ["art deco pattern", "deco design", "gatsby aesthetic"],
            "Art Déco Géométrique": {"_keywords": ["deco geometric", "deco shapes", "twenties pattern"]},
            "Art Déco Floral": {"_keywords": ["deco floral", "deco botanical", "twenties flowers"]},
        },
        "Rétro & Vintage": {
            "_keywords": ["retro pattern", "vintage design", "nostalgic aesthetic"],
            "Années 50-60": {"_keywords": ["50s pattern", "60s design", "atomic age", "mid century modern"]},
            "Années 70-80": {"_keywords": ["70s pattern", "80s design", "groovy", "disco era"]},
            "Publicité Vintage": {"_keywords": ["vintage advertising", "retro ad style", "vintage poster"]},
        },
        "Minimaliste": {
            "_keywords": ["minimalist pattern", "minimal design", "clean aesthetic"],
        },
        "Folk & Traditionnel": {
            "_keywords": ["folk art pattern", "traditional design", "naive art"],
            "Folk Scandinave": {"_keywords": ["scandinavian folk", "nordic folk art", "dala horse"]},
            "Folk Mexicain": {"_keywords": ["mexican folk art", "otomi", "huichol", "oaxacan"]},
            "Folk Est-Européen": {"_keywords": ["eastern european folk", "slavic pattern", "ukrainian folk art"]},
        },
    },
    "Mystique & Spirituel": {
        "_keywords": ["mystical pattern", "spiritual design", "esoteric art"],
        "Tarot": {
            "_keywords": ["tarot design", "tarot art", "oracle cards"],
            "Tarot Moderne": {"_keywords": ["modern tarot", "contemporary tarot", "indie tarot"]},
            "Tarot Cottagecore": {"_keywords": ["cottagecore tarot", "nature tarot", "botanical tarot"]},
            "Tarot Gothique": {"_keywords": ["gothic tarot", "dark tarot", "macabre tarot"]},
        },
        "Astrologie": {
            "_keywords": ["astrology pattern", "zodiac design", "celestial chart"],
            "Signes du Zodiaque": {"_keywords": ["zodiac signs", "star signs", "horoscope design"]},
            "Constellations": {"_keywords": ["constellation pattern", "star map", "night sky chart"]},
        },
        "Cristaux & Gemmes": {
            "_keywords": ["crystal pattern", "gemstone design", "mineral art"],
            "Cristaux Aquarelle": {"_keywords": ["watercolor crystals", "painted gems", "crystal illustration"]},
        },
        "Céleste": {
            "_keywords": ["celestial pattern", "moon stars design", "cosmic art"],
            "Lune & Étoiles": {"_keywords": ["moon and stars", "lunar pattern", "star pattern"]},
            "Soleil & Lune": {"_keywords": ["sun and moon", "solar lunar", "celestial faces"]},
            "Galaxie & Cosmos": {"_keywords": ["galaxy pattern", "nebula design", "space art"]},
        },
    },
    "Culturel & Ethnique": {
        "_keywords": ["cultural pattern", "ethnic design", "world art"],
        "Japonais": {
            "_keywords": ["japanese pattern", "japan design", "nihon art"],
            "Japonais Traditionnel": {"_keywords": ["traditional japanese", "kimono pattern", "ukiyo e"]},
            "Sakura": {"_keywords": ["cherry blossom", "sakura pattern", "hanami"]},
            "Koi": {"_keywords": ["koi fish", "koi pattern", "japanese fish"]},
        },
        "Scandinave": {
            "_keywords": ["scandinavian pattern", "nordic design", "hygge aesthetic"],
            "Noël Scandinave": {"_keywords": ["scandinavian christmas", "nordic holiday", "hygge christmas"]},
        },
        "Marocain": {
            "_keywords": ["moroccan pattern", "arabesque design", "moorish art"],
            "Zellige": {"_keywords": ["zellige pattern", "moroccan tile", "islamic tile"]},
        },
        "Mexicain": {
            "_keywords": ["mexican pattern", "día de muertos", "folk mexico"],
            "Día de Muertos": {"_keywords": ["day of the dead", "sugar skull", "calavera pattern"]},
        },
        "Celtique": {
            "_keywords": ["celtic pattern", "celtic knot", "irish design"],
            "Entrelacs Celtiques": {"_keywords": ["celtic knotwork", "interlace pattern", "trinity knot"]},
        },
        "Africain": {
            "_keywords": ["african pattern", "kente", "tribal africa"],
            "Kente & Ankara": {"_keywords": ["kente pattern", "ankara fabric", "adire"]},
        },
        "Indien": {
            "_keywords": ["indian pattern", "mandala", "paisley design"],
            "Mandala": {"_keywords": ["mandala pattern", "henna design", "rangoli"]},
            "Paisley": {"_keywords": ["paisley pattern", "boteh design", "kashmir pattern"]},
        },
    },
    "Saisonnier": {
        "_keywords": ["seasonal pattern", "holiday design", "time of year"],
        "Noël": {
            "_keywords": ["christmas pattern", "holiday design", "festive"],
            "Noël Traditionnel": {"_keywords": ["traditional christmas", "classic christmas", "holly berries"]},
            "Noël Scandinave": {"_keywords": ["scandinavian christmas", "nordic xmas", "hygge holiday"]},
            "Noël Gothique": {"_keywords": ["gothic christmas", "dark christmas", "creepy christmas"]},
            "Noël Rétro": {"_keywords": ["retro christmas", "vintage holiday", "50s christmas"]},
        },
        "Halloween": {
            "_keywords": ["halloween pattern", "spooky design", "autumn horror"],
            "Halloween Mignon": {"_keywords": ["cute halloween", "kawaii halloween", "friendly spooky"]},
            "Halloween Gothique": {"_keywords": ["gothic halloween", "dark halloween", "horror halloween"]},
            "Halloween Cottagecore": {"_keywords": ["cottagecore halloween", "autumn witch", "harvest halloween"]},
        },
        "Printemps & Pâques": {
            "_keywords": ["spring pattern", "easter design", "renewal theme"],
        },
        "Été": {
            "_keywords": ["summer pattern", "warm season design", "sunshine theme"],
        },
        "Automne": {
            "_keywords": ["autumn pattern", "fall design", "harvest theme"],
            "Automne Cottagecore": {"_keywords": ["cottagecore autumn", "cozy fall", "harvest cottage"]},
        },
        "Hiver": {
            "_keywords": ["winter pattern", "cold season design", "snowflake theme"],
        },
    },
    "Espace & Cosmos": {
        "_keywords": ["space pattern", "cosmic design", "astronomy art"],
        "Espace Réaliste": {"_keywords": ["realistic space", "nasa photography style", "astronomical art"]},
        "Espace Cartoon": {"_keywords": ["cute space", "cartoon planets", "kawaii cosmos"]},
        "Espace Rétro": {"_keywords": ["retro space", "50s space", "pulp sci fi", "retro nasa"]},
    },
    "Médiéval & Fantasy": {
        "_keywords": ["medieval pattern", "fantasy design", "mythical art"],
        "Médiéval": {
            "_keywords": ["medieval design", "middle ages art", "heraldic"],
            "Héraldique": {"_keywords": ["heraldic pattern", "coat of arms", "armorial"]},
            "Manuscrit Enluminé": {"_keywords": ["illuminated manuscript", "medieval illumination", "book of hours"]},
            "Plantes Médiévales": {"_keywords": ["medieval plants", "herbal medieval", "apothecary medieval"]},
        },
        "Fantasy": {
            "_keywords": ["fantasy art", "magical world", "high fantasy"],
            "Elfique & Fae": {"_keywords": ["elven design", "fae art", "fairy realm"]},
            "Sorcellerie": {"_keywords": ["sorcery art", "wizard design", "alchemy pattern"]},
        },
        "Steampunk": {
            "_keywords": ["steampunk design", "clockwork pattern", "victorian sci fi"],
        },
    },
}


def _parse_tree(
    raw: Dict,
    parent: Optional[str] = None,
    level: int = 0,
    nodes: Optional[Dict[str, NicheNode]] = None,
) -> Dict[str, NicheNode]:
    if nodes is None:
        nodes = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        node = NicheNode(
            name=key,
            parent=parent,
            level=level,
            keywords=value.get("_keywords", []),
        )
        # Find children
        children = [k for k in value if not k.startswith("_") and isinstance(value[k], dict)]
        node.children = children
        nodes[key] = node
        _parse_tree(value, parent=key, level=level + 1, nodes=nodes)
    return nodes


class NicheTree:
    """
    Phase 3 — Hierarchical niche decomposition.

    Provides traversal, lookup, and decomposition of the POD niche ontology.
    """

    def __init__(self):
        self._nodes: Dict[str, NicheNode] = _parse_tree(_RAW_TREE)

    def get(self, name: str) -> Optional[NicheNode]:
        """Get a node by exact name."""
        return self._nodes.get(name)

    def children_of(self, name: str) -> List[NicheNode]:
        """Return all direct children of a node."""
        node = self._nodes.get(name)
        if not node:
            return []
        return [self._nodes[c] for c in node.children if c in self._nodes]

    def all_descendants(self, name: str) -> List[NicheNode]:
        """Return all descendants (BFS) of a node."""
        result = []
        queue = self.children_of(name)
        while queue:
            node = queue.pop(0)
            result.append(node)
            queue.extend(self.children_of(node.name))
        return result

    def ancestors_of(self, name: str) -> List[NicheNode]:
        """Return the ancestor chain from root to this node (exclusive)."""
        node = self._nodes.get(name)
        if not node or not node.parent:
            return []
        ancestors = []
        current = node.parent
        while current:
            ancestor = self._nodes.get(current)
            if not ancestor:
                break
            ancestors.insert(0, ancestor)
            current = ancestor.parent
        return ancestors

    def root_nodes(self) -> List[NicheNode]:
        """Return top-level nodes (level 0)."""
        return [n for n in self._nodes.values() if n.level == 0]

    def all_leaves(self) -> List[NicheNode]:
        """Return all leaf nodes (no children) — the most specific sub-niches."""
        return [n for n in self._nodes.values() if not n.children]

    def niches_at_level(self, level: int) -> List[NicheNode]:
        """Return all nodes at a given depth level."""
        return [n for n in self._nodes.values() if n.level == level]

    def all_nodes(self) -> List[NicheNode]:
        """Return every node in the tree."""
        return list(self._nodes.values())

    def search(self, query: str) -> List[NicheNode]:
        """
        Find nodes whose name or keywords match the query (case-insensitive).
        """
        q = query.lower()
        matches = []
        for node in self._nodes.values():
            if q in node.name.lower() or any(q in kw.lower() for kw in node.keywords):
                matches.append(node)
        return matches

    def path_to(self, name: str) -> str:
        """Return a breadcrumb path string, e.g. 'Nature & Botanique > Herboristerie > Apothicaire'."""
        ancestors = self.ancestors_of(name)
        parts = [a.name for a in ancestors] + [name]
        return " > ".join(parts)

    def decompose(self, name: str) -> Dict:
        """
        Return a full decomposition of a niche into its tree context.

        Returns:
            {
                "name": str,
                "path": str,
                "level": int,
                "parent": str | None,
                "children": [str],
                "siblings": [str],
                "keywords": [str],
            }
        """
        node = self._nodes.get(name)
        if not node:
            return {}
        siblings = []
        if node.parent:
            parent_node = self._nodes.get(node.parent)
            if parent_node:
                siblings = [c for c in parent_node.children if c != name]
        return {
            "name": node.name,
            "path": self.path_to(name),
            "level": node.level,
            "parent": node.parent,
            "children": node.children,
            "siblings": siblings,
            "keywords": node.keywords,
        }

    def all_search_terms(self, name: str) -> List[str]:
        """
        Return all search terms for a node: its own keywords + ancestor keywords
        — useful for building comprehensive scraper queries.
        """
        node = self._nodes.get(name)
        if not node:
            return []
        terms = list(node.keywords)
        for ancestor in self.ancestors_of(name):
            terms.extend(ancestor.keywords)
        return list(dict.fromkeys(terms))  # deduplicate

    def print_tree(self, root: Optional[str] = None, indent: int = 0):
        """Debug helper: print the niche tree to stdout."""
        if root is None:
            for r in self.root_nodes():
                self.print_tree(r.name, indent=0)
            return
        node = self._nodes.get(root)
        if not node:
            return
        prefix = "  " * indent + ("├── " if indent > 0 else "")
        print(f"{prefix}{node.name}")
        for child in node.children:
            self.print_tree(child, indent + 1)
