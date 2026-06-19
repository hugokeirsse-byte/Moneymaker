#!/usr/bin/env bash
# fetch_fonts.sh — télécharge le roster de polices utilisé par typo_fonts.py.
# assets/fonts/ est gitignoré : ce script reconstitue les polices (CI / local).
# Usage : bash scripts/fetch_fonts.sh
set -euo pipefail

DIR="assets/fonts"
mkdir -p "$DIR"
BASE="https://raw.githubusercontent.com/google/fonts/main"

# nom_fichier  url
fetch() {
  local name="$1" url="$2"
  if [ -s "$DIR/$name" ]; then
    echo "skip $name (déjà présent)"
    return
  fi
  if curl -fsSL "$url" -o "$DIR/$name" && [ -s "$DIR/$name" ]; then
    echo "ok   $name"
  else
    echo "FAIL $name ($url)" >&2
  fi
}

fetch "Anton.ttf"                "$BASE/ofl/anton/Anton-Regular.ttf"
fetch "Oswald-Bold.ttf"          "$BASE/ofl/oswald/Oswald%5Bwght%5D.ttf"
fetch "BebasNeue-Regular.ttf"    "$BASE/ofl/bebasneue/BebasNeue-Regular.ttf"
fetch "ArchivoBlack-Regular.ttf" "$BASE/ofl/archivoblack/ArchivoBlack-Regular.ttf"
fetch "FjallaOne-Regular.ttf"    "$BASE/ofl/fjallaone/FjallaOne-Regular.ttf"
fetch "Bangers-Regular.ttf"      "$BASE/ofl/bangers/Bangers-Regular.ttf"
fetch "PermanentMarker.ttf"      "$BASE/apache/permanentmarker/PermanentMarker-Regular.ttf"
fetch "AbrilFatface.ttf"         "$BASE/ofl/abrilfatface/AbrilFatface-Regular.ttf"
fetch "PlayfairDisplay-Bold.ttf" "$BASE/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
fetch "Caveat-Bold.ttf"          "$BASE/ofl/caveat/Caveat%5Bwght%5D.ttf"
fetch "Kaushan_Script.ttf"       "$BASE/ofl/kaushanscript/KaushanScript-Regular.ttf"
fetch "Lobster.ttf"              "$BASE/ofl/lobster/Lobster-Regular.ttf"
fetch "Pacifico.ttf"             "$BASE/ofl/pacifico/Pacifico-Regular.ttf"
fetch "SpaceMono-Bold.ttf"       "$BASE/ofl/spacemono/SpaceMono-Bold.ttf"
fetch "JetBrainsMono-Bold.ttf"   "$BASE/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf"
fetch "Poppins-Bold.ttf"         "$BASE/ofl/poppins/Poppins-Bold.ttf"
fetch "Sora-Bold.ttf"            "$BASE/ofl/sora/Sora%5Bwght%5D.ttf"

echo "roster : $(ls -1 "$DIR" | wc -l) polices dans $DIR"
