# ALICE — agent local intelligent, routeur, mémoire, MCP

ALICE est un agent IA local qui tourne sur une machine Ubuntu (sans GPU) :
elle lit une **carte vivante** (circuits/étapes/outils), tient une
**mémoire procédurale** (SQLite), fait de l'**OCR** via Tesseract, et ne
sollicite le modèle local (Qwen2.5-3B, llama.cpp) qu'en dernier recours.

Elle est exposée aux autres agents via l'API **gate** (`/api/v1/gate`) et
un serveur **MCP** (stdio).

## Architecture

```
Requête ─▶ gate :8000 ─▶ routeur.py ─┬─ carte vivante (cartes.json)
                                      ├─ mémoire (SQLite, memory.py)
                                      ├─ outils (OCR / actions shell)
                                      └─ repli : modèle local Qwen (llama-server :8081)
```

- `routeur.py` — chef d'orchestre : carte → mémoire → outils → modèle.
  Seuil de confiance carte : **0.6** (anti faux positifs), mots génériques exclus.
- `memory.py` — carnet de procédures SQLite (`procedures_memoire`), recherche par
  nom exact → contient → mots significatifs.
- `adaptateur_carte.py` — lecture de la carte vivante (zones, nœuds, circuits).
- `alice_gate.py` — API :8000 : `POST /api/v1/gate` (async, `job_id`),
  `GET /api/v1/gate/<id>`, `POST /api/v1/ocr`.
- `mcp_alice.py` — serveur MCP stdio : `lire_carte`, `lancer_circuit`,
  `demander_alice`.
- `outils/ocr.py` — OCR Tesseract (binaire local dans `~/alice-local`, langue fra,
  replis `--psm` 6/7).
- `test_alice.py` — suite de validation gate (6 tests) ;
  `alicization/tests/` — suite complète du routeur/mémoire/carte.

## Installation

```bash
# Dépendances
python3 -m pip install -r requirements.txt

# Tesseract (optionnel) : `sudo apt install tesseract-ocr tesseract-ocr-fra`
# Implémentation sans sudo → extraire les .deb dans ~/alice-local
# (outils/ocr.py le détecte via BIN_TESSERACT / LD_LIBRARY_PATH / TESSDATA_PREFIX)
```

## Démarrage

```bash
# 1. Modèle local (llama.cpp, port 8081)
llama-server -m models/qwen2.5-3b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8081

# 2. Gate (API :8000)
python3 alice_gate.py          # POST /api/v1/gate {"command":"Trouver 712"}

# 3. MCP (stdio, pour opencode)
python3 mcp_alice.py
```

## MCP — configuration opencode

Ajoute ce bloc à `~/.config/opencode/opencode.json` puis redémarre opencode :

```json
{
  "mcp": {
    "alice": {
      "type": "local",
      "command": ["/home/alice/alicization-venv/bin/python", "/home/alice/mcp_alice.py"],
      "enabled": true,
      "environment": { "GITHUB_TOKEN": "{env:GITHUB_TOKEN}" }
    }
  }
}
```

## Tests

```bash
python3 test_alice.py                 # gate 6/6
cd alicization && python3 -m unittest discover -s tests   # 109 tests
```

## Licence

MIT — voir `LICENSE`.