# Cahier des charges — Designs POD (typographie & word-shapes)

> Document de référence à transmettre à un assistant (Gemini, etc.) pour qu'il
> génère **de nouvelles idées** dans le même esprit. Il décrit ce qu'on fabrique,
> comment, et ce qui fait une bonne idée par famille.

---

## 1. Principes communs (valables pour TOUTES les familles)

- **Marché** : print-on-demand (Redbubble, Amazon Merch, etc.), surtout US/UK,
  puis FR/DE/ES/IT.
- **Support** : t-shirts, stickers, posters, mugs… → le visuel doit marcher en
  petit comme en grand.
- **Technique** : PNG **fond 100 % transparent**, **4500 px** de côté, 300 DPI.
- **Deux variantes maillot** quand c'est du texte : encre **sombre** (maillots
  clairs) + encre **blanche** (maillots foncés). Les couleurs saturées (rouge,
  vert, bleu…) restent identiques ; seuls les neutres sombres basculent.
- **Zéro propriété intellectuelle** : aucune marque déposée, logo, parole de
  chanson/film, personnage. Uniquement mots du dictionnaire, tournures
  folkloriques, humour générique, concepts géographiques.
- **Pas de vulgarité frontale** (sexe explicite) : filtré/dépublié sur les
  grosses plateformes. L'edgy passe par l'absurde et le cynisme, pas le cru.
- **Ce qui vend** : le **relatable** (« c'est tellement moi ») et l'**humour
  pince-sans-rire**. Le choc pur vend mal et se fait retirer.
- **Polices** : roster maison dans `assets/fonts/` (Anton, Bebas, Pacifico,
  Playfair, Abril Fatface, Space Mono…). Cf. `scripts/typo_fonts.py`.

---

## 2. Les familles de produits

### A. Phrases « relatable » (déadpan / sarcasme tendre)  → le plus rentable
- **Concept** : une punchline courte qui décrit un état d'esprit ; l'acheteur se
  reconnaît. Ton : fatigue, introversion, sarcasme doux, auto-dérision.
- **Forme** : 1 à 3 lignes, **Pacifico** (script), casse Titre, 1 mot accentué
  en **rouge**. Le contraste écriture mignonne / propos cynique fait l'effet.
- **Exemples** : *Professionally Tired* · *Mildly Feral* · *Emotional Support
  Overthinker* · *Powered by Caffeine & Anxiety* · *Out of Office Mentally*.
- **Bonne idée** : universelle, lisible en 2 s, vraie en vrai, originale (pas un
  proverbe connu). Évite le méchant ; vise le « moi exactement ».
- **Script** : `scripts/gen_relatable.py`

### B. Mots « à la mode » / cynisme (zeitgeist)
- **Concept** : le vocabulaire qui tourne en ce moment, en gros.
- **Forme** : idem A (Pacifico, accent rouge, 2 variantes), parfois une rature.
- **Exemples** : *Overrated* (raturé) · *Delulu* · *Let Me Overthink This* ·
  *Touch Grass (Maybe)* · *Chronically Online* · *Aggressively Average*.
- **Bonne idée** : un mot/expression à la mode, tournure ironique, jeu de mots
  léger (overrated/underrated/wonderrated).
- **Script** : `scripts/gen_trendy.py`

### C. « [Verbe]-moi en [langue] » (FR + EN)
- **Concept** : un verbe (souvent rude, parfois tendre) + une langue réputée
  pour sonner agressive ou romantique. Gag culturel.
- **Forme** : petit verbe manuscrit au-dessus + **GRANDE langue**, typo qui colle
  à la langue (allemand = bloc froid, italien = serif chic, russe = capitales
  rouges…). 2 variantes maillot.
- **Exemples** : *brutalise-moi EN PORTUGAIS* · *insulte-moi EN ALLEMAND* ·
  *câline-moi EN ITALIEN* · *humiliate me IN RUSSIAN*.
- **Bonne idée** : verbe expressif + langue à fort cliché sonore. Contraste
  rude/tendre bienvenu.
- **Script** : `scripts/gen_speak_to_me.py`

### D. Geek / fan (style terminal)
- **Concept** : niches de fans, clin d'œil codeur. « insulte/susurre-moi en
  [langue fictive] ».
- **Forme** : police mono, espaces → underscores, prompt `>`, curseur bloc
  coloré, parfois une ligne en binaire. 2 variantes.
- **Exemples** : `> insulte_moi` **EN_KLINGON▮** · *IN_ELVISH* · *IN_BINARY*
  (avec « LOVE » en binaire dessous).
- **Bonne idée** : référence geek générique (binaire, langues construites,
  vocabulaire dev) — **sans nom de marque protégé**.
- **Script** : `scripts/gen_geek_phrases.py`

### E. Absurde « lunaire » (pince-sans-rire)
- **Concept** : deux mots sortis de nulle part, au premier degré, façon badge
  officiel. Certains riment.
- **Forme** : grosse typo bold (Anton/Archivo Black/Bebas), 2e mot en couleur.
- **Exemples** : *Facteur Dompteur* · *Plombier Lunaire* · *Dentiste Viking* ·
  *Plongeur Vengeur* · *Pigeon Tactique*.
- **Bonne idée** : un mot sérieux (métier, statut) + un mot improbable. Drôle
  par le sérieux du ton, pas par la vulgarité.
- **Script** : `scripts/gen_lunaire.py`

### F. Phrases « food » absurdes
- **Concept** : aliment réconfortant + valeur abstraite, ton décalé.
- **Forme** : typo qui fait écho (charcuterie en serif chaud, etc.), 2 variantes.
- **Exemples** : *Du Pâté et de l'Espoir* · *Plus de Fromage Moins de Problèmes*.
- **À localiser par marché** : l'équivalent culturel qui parle là-bas
  (bière/saucisse en DE, bacon/coffee en US…).
- **Script** : `scripts/gen_absurd_phrases.py`

### G. Word-shapes « pays » (mots dans la silhouette d'un pays)
- **Concept** : remplir la **forme réelle d'un pays** avec des mots d'un thème :
  argot, gros mots, insultes anciennes, mots désuets rigolos.
- **Forme** : silhouette GeoJSON, patch blanc + bordure, mots en Anton ;
  version couleurs du drapeau **et** version noir & blanc.
- **Exemples** : France remplie d'argot (*Bagnole, Clope, Meuf…*), d'insultes
  désuètes (*Faquin, Maraud…*), de mots désuets (*Coquecigrue, Galimatias…*).
- **Bonne idée** : un pays + un champ lexical local fort et reconnaissable.
- **Script** : `scripts/gen_wordcloud.py --mask country:france`

### H. Word-shapes « États US » (NOUVEAU)
- **Concept** : la **forme d'un État américain** remplie de mots typiques de
  cet État (bouffe, culture, surnoms, paysages, clichés positifs).
- **Forme** : silhouette GeoJSON, patch blanc + bordure, Anton ; version
  bleu marine **et** noir & blanc.
- **Exemples** : Texas (*BBQ, Cowboy, Rodeo, Longhorn, Lone Star, Alamo…*),
  Californie (*Surf, Hollywood, Redwood, Tacos, Golden State…*).
- **Bonne idée** : un État + 25-35 mots emblématiques (fierté locale, ça se
  vend à ceux qui y vivent / en sont originaires).
- **Script** : `scripts/gen_wordcloud.py --mask usstate:texas`

### I. Word-shapes « passions / niches » (mots dans une silhouette d'objet)
- **Concept** : remplir une **silhouette liée à un hobby** avec le vocabulaire
  de ce hobby. La forme dit le sujet d'un coup d'œil.
- **Forme** : silhouette (emoji Noto OFL ou icône CC0), mots Anton, contour net,
  palette thématique (océan pour la pêche, forêt pour les champignons…).
- **Exemples** : pêche → **poisson** (*Angler, Reel, Bass, Lure…*), cueillette →
  **champignon** (*Forager, Chanterelle, Porcini…*).
- **Bonne idée** : un hobby populaire + une silhouette évidente + 25-35 termes
  d'initié (les pratiquants adorent le jargon).
- **Script** : `scripts/gen_wordcloud.py --mask <forme>.png`

### J. Insultes typographiques (mono-mot & multi-langues)
- **Concept** : un seul mot d'insulte/argot ancien en belle typo ; ou une
  collection « une insulte par pays ».
- **Forme** : mot seul centré, belle police ; collection = grosse typo + pays.
- **Exemples** : *Gourgandine*, *Faquin* ; collection 25 pays (*Amadán* IE,
  *Dummkopf* DE, *Pendejo* MX…).
- **Script** : `scripts/gen_insult_poster.py`, `scripts/gen_insult_collection.py`

---

## 3. Idées de nouvelles directions (à creuser)

- **Métiers / hobbies relatable** : « Professionally Tired » décliné par métier
  (*Nurse Mode: Survival*, *Teacher: Powered by Coffee & Chaos*).
- **Animaux de compagnie** : silhouettes chat/chien remplies de mots de « cat/dog
  parent », ou punchlines (*Emotional Support Cat*).
- **Villes** (comme les États) : silhouette d'une skyline / mots d'une ville.
- **Signes astro / MBTI** : punchlines relatable par profil.
- **Saisonnier** : Halloween (*Mildly Spooky*), Noël anti-fête (*Bah Humbug,
  Politely*) — fort pic de ventes.
- **Sports & plein air** : word-shapes (ballon, montagne) + jargon.
- **Jeux de mots visuels** : un pictogramme simple + un twist (ex. un soleil
  d'une couleur inattendue qui évoque une autre référence — à manier finement).

---

## 4. Prompt prêt à coller pour Gemini

> Tu es directeur créatif pour une boutique print-on-demand (t-shirts, stickers)
> sur Redbubble/Amazon Merch, marchés US/UK puis FR/DE/ES/IT. Voici nos familles
> de produits : [coller les sections 2.A à 2.J].
>
> Contraintes : zéro marque déposée / parole / personnage ; pas de vulgarité
> sexuelle explicite ; humour relatable ou pince-sans-rire ; lisible en 2 s.
>
> Donne-moi **30 idées nouvelles** pour la famille « ___ » (au choix), sous forme
> de tableau : `idée | texte exact | pourquoi ça vend | mot à accentuer`.
> Évite les clichés déjà vus, vise l'original et le « c'est tellement moi ».

---

*Maj : voir `scripts/` pour les générateurs et `produits/` pour les rendus.*
