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
    "Nature & Botanical": {
        "_keywords": ["botanical pattern", "nature design", "plant pattern"],
        "Floral": {
            "_keywords": ["floral pattern", "flower design", "botanical flowers"],
            "Roses & Peonies": {"_keywords": ["roses pattern", "peonies", "rosa peony"]},
            "Wildflowers": {"_keywords": ["wildflowers", "meadow flowers", "wildflower meadow"]},
            "Ditsy Floral": {"_keywords": ["ditsy floral", "small flowers pattern", "tiny flowers"]},
            "Tropical Flowers": {"_keywords": ["tropical flowers", "hibiscus", "bird of paradise"]},
        },
        "Botanical": {
            "_keywords": ["botanical illustration", "plant illustration", "botanical art"],
            "Victorian Botanical": {"_keywords": ["victorian botanical", "antique botanical", "vintage botanical print"]},
            "Scientific Botanical": {"_keywords": ["scientific illustration", "natural history print", "herbarium"]},
            "Ferns & Moss": {"_keywords": ["fern pattern", "moss design", "ferns forest floor"]},
            "Succulents": {"_keywords": ["succulent pattern", "cactus design", "desert plants"]},
        },
        "Herbalism": {
            "_keywords": ["herbal pattern", "herbs design", "medicinal plants"],
            "Apothecary": {"_keywords": ["apothecary", "apothecary bottles", "potion herbs"]},
            "Witch Garden": {"_keywords": ["witch garden", "witch herbs", "magical plants"]},
            "Medieval Medicinal Plants": {"_keywords": ["medieval herbs", "medieval medicine", "illuminated manuscript plants"]},
            "Culinary Herbs": {"_keywords": ["kitchen herbs", "cooking herbs", "culinary plants"]},
        },
        "Mushrooms": {
            "_keywords": ["mushroom pattern", "fungi design", "toadstool"],
            "Wild Mushrooms": {"_keywords": ["wild mushrooms", "forest mushrooms", "amanita"]},
            "Cute Mushrooms": {"_keywords": ["cute mushrooms", "kawaii mushroom", "cartoon mushroom"]},
            "Psychedelic Mushrooms": {"_keywords": ["psychedelic mushroom", "magic mushroom art", "trippy fungi"]},
        },
        "Forest & Woodland": {
            "_keywords": ["forest pattern", "woodland design", "trees pattern"],
            "Enchanted Forest": {"_keywords": ["enchanted forest", "magical forest", "fairy forest"]},
            "Dark Woods": {"_keywords": ["dark forest", "moody forest", "gothic forest"]},
            "Boreal Forest": {"_keywords": ["boreal forest", "pine forest", "nordic forest taiga"]},
        },
        "Ocean & Marine": {
            "_keywords": ["ocean pattern", "marine design", "sea pattern"],
            "Underwater": {"_keywords": ["underwater pattern", "coral reef", "deep sea"]},
            "Coastal & Beach": {"_keywords": ["coastal pattern", "beach design", "nautical"]},
            "Sea Creatures": {"_keywords": ["sea creatures", "jellyfish pattern", "seahorse pattern"]},
        },
        "Tropical": {
            "_keywords": ["tropical pattern", "jungle design", "tropics"],
            "Tropical Leaves": {"_keywords": ["tropical leaves", "palm leaf", "monstera pattern"]},
            "Tropical Birds": {"_keywords": ["tropical birds", "parrot pattern", "toucan design"]},
        },
    },
    "Animals": {
        "_keywords": ["animal pattern", "wildlife design", "creature pattern"],
        "Cats": {
            "_keywords": ["cat pattern", "cats design", "feline pattern"],
            "Cute Cats": {"_keywords": ["cute cats", "kawaii cats", "cartoon cats"]},
            "Realistic Cats": {"_keywords": ["realistic cat", "watercolor cat", "cat portrait"]},
            "Mystical Cats": {"_keywords": ["black cat", "witch cat", "mystical cat celestial"]},
        },
        "Dogs": {
            "_keywords": ["dog pattern", "dogs design", "canine pattern"],
            "Purebred Dogs": {"_keywords": ["dachshund pattern", "corgi pattern", "breed specific dog"]},
        },
        "Woodland Animals": {
            "_keywords": ["woodland animals", "forest creatures", "woodland critters"],
            "Foxes": {"_keywords": ["fox pattern", "foxes design", "woodland fox"]},
            "Deer": {"_keywords": ["deer pattern", "stag design", "forest deer"]},
            "Rabbits": {"_keywords": ["rabbit pattern", "bunny design", "hare pattern"]},
            "Hedgehogs": {"_keywords": ["hedgehog pattern", "hedgehog design"]},
            "Squirrels": {"_keywords": ["squirrel pattern", "squirrel design"]},
        },
        "Birds": {
            "_keywords": ["bird pattern", "birds design", "avian pattern"],
            "Ravens & Crows": {"_keywords": ["raven pattern", "crow design", "dark birds"]},
            "Owls": {"_keywords": ["owl pattern", "owl design", "owl art"]},
            "Songbirds": {"_keywords": ["songbird pattern", "garden birds", "robin wren"]},
        },
        "Insects": {
            "_keywords": ["insect pattern", "bugs design", "entomology art"],
            "Butterflies": {"_keywords": ["butterfly pattern", "butterfly design", "lepidoptera"]},
            "Moths": {"_keywords": ["moth pattern", "hawk moth", "luna moth"]},
            "Bees": {"_keywords": ["bee pattern", "honeybee design", "bumblebee pattern"]},
            "Beetles": {"_keywords": ["beetle pattern", "bug art", "scarab design"]},
        },
        "Mythical Animals": {
            "_keywords": ["mythical animals", "fantasy creatures", "magical beasts"],
            "Unicorns": {"_keywords": ["unicorn pattern", "unicorn design", "rainbow unicorn"]},
            "Dragons": {"_keywords": ["dragon pattern", "dragon design", "serpent dragon"]},
        },
    },
    "Aesthetic Styles": {
        "_keywords": ["aesthetic pattern", "style design", "trend aesthetic"],
        "Cottagecore": {
            "_keywords": ["cottagecore pattern", "cottage aesthetic", "rural charm"],
            "Romantic Cottagecore": {"_keywords": ["romantic cottage", "english cottage garden", "cottage roses"]},
            "Autumn Cottagecore": {"_keywords": ["autumn cottagecore", "fall cottagecore", "harvest cottage"]},
        },
        "Dark Academia": {
            "_keywords": ["dark academia", "academic aesthetic", "gothic scholarly"],
            "Dark Academia Botanical": {"_keywords": ["dark botanical", "moody botanical", "gothic plant"]},
        },
        "Goblincore": {
            "_keywords": ["goblincore", "goblin aesthetic", "frogcore"],
            "Goblincore Mushrooms": {"_keywords": ["goblin mushrooms", "mushroom hoard", "forest goblin"]},
        },
        "Fairycore": {
            "_keywords": ["fairycore", "fairy aesthetic", "fae garden"],
            "Fairy Cottagecore": {"_keywords": ["fairy cottage", "enchanted garden", "flower fairy"]},
        },
        "Witchy & Occult": {
            "_keywords": ["witchy aesthetic", "occult design", "magic pattern"],
            "Modern Witchy": {"_keywords": ["modern witch", "hedge witch", "kitchen witch"]},
            "Gothic Witchy": {"_keywords": ["gothic witch", "dark witch", "halloween witch"]},
        },
        "Gothic": {
            "_keywords": ["gothic pattern", "dark aesthetic", "goth design"],
            "Victorian Gothic": {"_keywords": ["victorian gothic", "mourning jewelry", "memento mori"]},
            "Romantic Gothic": {"_keywords": ["romantic gothic", "dark romance", "gothic floral"]},
        },
        "Japandi": {
            "_keywords": ["japandi design", "japanese minimalism", "wabi sabi"],
        },
        "Boho": {
            "_keywords": ["boho pattern", "bohemian design", "hippie aesthetic"],
            "Boho Geometric": {"_keywords": ["boho geometric", "tribal geometric", "aztec pattern"]},
            "Boho Floral": {"_keywords": ["boho floral", "bohemian flowers", "free spirit floral"]},
        },
        "Solarpunk": {
            "_keywords": ["solarpunk design", "eco punk", "green future aesthetic"],
        },
        "Cyberpunk": {
            "_keywords": ["cyberpunk pattern", "neon aesthetic", "tech dystopian"],
        },
    },
    "Graphic Styles": {
        "_keywords": ["graphic style pattern", "design style", "pattern style"],
        "Geometric": {
            "_keywords": ["geometric pattern", "shapes design", "tessellation"],
            "Minimalist Geometric": {"_keywords": ["minimal geometric", "clean shapes", "simple geometry"]},
            "Complex Geometric": {"_keywords": ["complex geometric", "mandala", "sacred geometry"]},
            "Organic Geometric": {"_keywords": ["organic geometric", "soft shapes", "blob pattern"]},
        },
        "Watercolor": {
            "_keywords": ["watercolor pattern", "painted design", "wash technique"],
            "Watercolor Floral": {"_keywords": ["watercolor flowers", "painted flowers", "floral wash"]},
            "Abstract Watercolor": {"_keywords": ["abstract watercolor", "color wash", "watercolor blur"]},
        },
        "Art Nouveau": {
            "_keywords": ["art nouveau pattern", "nouveau design", "jugendstil"],
            "Art Nouveau Floral": {"_keywords": ["art nouveau flowers", "nouveau botanical", "mucha style"]},
            "Art Nouveau Animals": {"_keywords": ["art nouveau animals", "nouveau creatures", "decorative animals"]},
        },
        "Art Deco": {
            "_keywords": ["art deco pattern", "deco design", "gatsby aesthetic"],
            "Art Deco Geometric": {"_keywords": ["deco geometric", "deco shapes", "twenties pattern"]},
            "Art Deco Floral": {"_keywords": ["deco floral", "deco botanical", "twenties flowers"]},
        },
        "Retro & Vintage": {
            "_keywords": ["retro pattern", "vintage design", "nostalgic aesthetic"],
            "50s-60s Retro": {"_keywords": ["50s pattern", "60s design", "atomic age mid century modern"]},
            "70s-80s Retro": {"_keywords": ["70s pattern", "80s design", "groovy disco era"]},
            "Vintage Advertising": {"_keywords": ["vintage advertising", "retro ad style", "vintage poster"]},
        },
        "Minimalist": {
            "_keywords": ["minimalist pattern", "minimal design", "clean aesthetic"],
        },
        "Folk & Traditional": {
            "_keywords": ["folk art pattern", "traditional design", "naive art"],
            "Scandinavian Folk": {"_keywords": ["scandinavian folk", "nordic folk art", "dala horse"]},
            "Mexican Folk Art": {"_keywords": ["mexican folk art", "otomi", "huichol oaxacan"]},
            "Eastern European Folk": {"_keywords": ["eastern european folk", "slavic pattern", "ukrainian folk art"]},
        },
    },
    "Mystical & Spiritual": {
        "_keywords": ["mystical pattern", "spiritual design", "esoteric art"],
        "Tarot": {
            "_keywords": ["tarot design", "tarot art", "oracle cards"],
            "Modern Tarot": {"_keywords": ["modern tarot", "contemporary tarot", "indie tarot"]},
            "Cottagecore Tarot": {"_keywords": ["cottagecore tarot", "nature tarot", "botanical tarot"]},
            "Gothic Tarot": {"_keywords": ["gothic tarot", "dark tarot", "macabre tarot"]},
        },
        "Astrology": {
            "_keywords": ["astrology pattern", "zodiac design", "celestial chart"],
            "Zodiac Signs": {"_keywords": ["zodiac signs", "star signs", "horoscope design"]},
            "Constellations": {"_keywords": ["constellation pattern", "star map", "night sky chart"]},
        },
        "Crystals & Gems": {
            "_keywords": ["crystal pattern", "gemstone design", "mineral art"],
            "Watercolor Crystals": {"_keywords": ["watercolor crystals", "painted gems", "crystal illustration"]},
        },
        "Celestial": {
            "_keywords": ["celestial pattern", "moon stars design", "cosmic art"],
            "Moon & Stars": {"_keywords": ["moon and stars", "lunar pattern", "star pattern"]},
            "Sun & Moon": {"_keywords": ["sun and moon", "solar lunar", "celestial faces"]},
            "Galaxy & Cosmos": {"_keywords": ["galaxy pattern", "nebula design", "space art"]},
        },
    },
    "Cultural & Ethnic": {
        "_keywords": ["cultural pattern", "ethnic design", "world art"],
        "Japanese": {
            "_keywords": ["japanese pattern", "japan design", "nihon art"],
            "Traditional Japanese": {"_keywords": ["traditional japanese", "kimono pattern", "ukiyo e"]},
            "Sakura": {"_keywords": ["cherry blossom", "sakura pattern", "hanami"]},
            "Koi": {"_keywords": ["koi fish", "koi pattern", "japanese fish"]},
        },
        "Scandinavian": {
            "_keywords": ["scandinavian pattern", "nordic design", "hygge aesthetic"],
            "Scandinavian Christmas": {"_keywords": ["scandinavian christmas", "nordic holiday", "hygge christmas"]},
        },
        "Moroccan": {
            "_keywords": ["moroccan pattern", "arabesque design", "moorish art"],
            "Zellige": {"_keywords": ["zellige pattern", "moroccan tile", "islamic tile"]},
        },
        "Mexican": {
            "_keywords": ["mexican pattern", "day of the dead", "folk mexico"],
            "Dia de Muertos": {"_keywords": ["day of the dead", "sugar skull", "calavera pattern"]},
        },
        "Celtic": {
            "_keywords": ["celtic pattern", "celtic knot", "irish design"],
            "Celtic Knotwork": {"_keywords": ["celtic knotwork", "interlace pattern", "trinity knot"]},
        },
        "African": {
            "_keywords": ["african pattern", "kente design", "tribal africa"],
            "Kente & Ankara": {"_keywords": ["kente pattern", "ankara fabric", "adire"]},
        },
        "Indian": {
            "_keywords": ["indian pattern", "mandala design", "paisley art"],
            "Mandala": {"_keywords": ["mandala pattern", "henna design", "rangoli"]},
            "Paisley": {"_keywords": ["paisley pattern", "boteh design", "kashmir pattern"]},
        },
    },
    "Seasonal": {
        "_keywords": ["seasonal pattern", "holiday design", "time of year"],
        "Christmas": {
            "_keywords": ["christmas pattern", "holiday design", "festive pattern"],
            "Traditional Christmas": {"_keywords": ["traditional christmas", "classic christmas", "holly berries"]},
            "Scandinavian Christmas": {"_keywords": ["scandinavian christmas", "nordic xmas", "hygge holiday"]},
            "Gothic Christmas": {"_keywords": ["gothic christmas", "dark christmas", "creepy christmas"]},
            "Retro Christmas": {"_keywords": ["retro christmas", "vintage holiday", "50s christmas"]},
        },
        "Halloween": {
            "_keywords": ["halloween pattern", "spooky design", "autumn horror"],
            "Cute Halloween": {"_keywords": ["cute halloween", "kawaii halloween", "friendly spooky"]},
            "Gothic Halloween": {"_keywords": ["gothic halloween", "dark halloween", "horror halloween"]},
            "Halloween Cottagecore": {"_keywords": ["cottagecore halloween", "autumn witch", "harvest halloween"]},
        },
        "Spring & Easter": {
            "_keywords": ["spring pattern", "easter design", "renewal theme"],
        },
        "Summer": {
            "_keywords": ["summer pattern", "warm season design", "sunshine theme"],
        },
        "Autumn": {
            "_keywords": ["autumn pattern", "fall design", "harvest theme"],
            "Autumn Cottagecore": {"_keywords": ["cottagecore autumn", "cozy fall", "harvest cottage"]},
        },
        "Winter": {
            "_keywords": ["winter pattern", "cold season design", "snowflake theme"],
        },
    },
    "Space & Cosmos": {
        "_keywords": ["space pattern", "cosmic design", "astronomy art"],
        "Realistic Space": {"_keywords": ["realistic space", "nasa photography style", "astronomical art"]},
        "Cartoon Space": {"_keywords": ["cute space", "cartoon planets", "kawaii cosmos"]},
        "Retro Space": {"_keywords": ["retro space", "50s space", "pulp sci fi retro nasa"]},
    },
    "Medieval & Fantasy": {
        "_keywords": ["medieval pattern", "fantasy design", "mythical art"],
        "Medieval": {
            "_keywords": ["medieval design", "middle ages art", "heraldic"],
            "Heraldry": {"_keywords": ["heraldic pattern", "coat of arms", "armorial"]},
            "Illuminated Manuscript": {"_keywords": ["illuminated manuscript", "medieval illumination", "book of hours"]},
            "Medieval Plants": {"_keywords": ["medieval plants", "herbal medieval", "apothecary medieval"]},
        },
        "Fantasy": {
            "_keywords": ["fantasy art", "magical world", "high fantasy"],
            "Elven & Fae": {"_keywords": ["elven design", "fae art", "fairy realm"]},
            "Sorcery & Wizardry": {"_keywords": ["sorcery art", "wizard design", "alchemy pattern"]},
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
