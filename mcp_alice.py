#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serveur MCP d'ALICE — expose Alice aux agents (opencode).
Fonctionne en stdio, exécuté localement sur la machine d'Alice.

Outils exposés :
  - lire_carte()            : vue d'ensemble de la carte vivante
  - lancer_circuit(nom)     : lance le circuit de la carte (étapes/actions)
  - demander_alice(message) : passe la requête au routeur d'Alice

Config opencode (~/.config/opencode/opencode.json) :
  "mcp": {
    "alice": {
      "type": "local",
      "command": ["/home/alice/alicization-venv/bin/python", "/home/alice/mcp_alice.py"],
      "enabled": true
    }
  }
"""
import sys
import json

sys.path.insert(0, "/home/alice/alicization")
sys.path.insert(0, "/home/alice")

import adaptateur_carte  # noqa: F401  (imports locaux d'Alice)

from mcp.server.mcpserver import MCPServer  # noqa: E402

from routeur import Routeur  # noqa: E402

mcp = MCPServer("alice")

_routeur = None


def _get_routeur():
    global _routeur
    if _routeur is None:
        _routeur = Routeur(
            chemin_carte="/home/alice/carte-vivante/cartes.json",
            chemin_db="/home/alice/alicization/state/alicization.db",
        )
    return _routeur


@mcp.tool()
def lire_carte() -> str:
    """Retourne une vue d'ensemble de la carte vivante d'Alice (zones, noeuds, circuits)."""
    try:
        r = _get_routeur()
        stats = r.carte_stats()
        noeuds = r.carte.get_tous_les_noeuds()
        resume = {
            "zones": stats["total_zones"],
            "noeuds": stats["total_noeuds"],
            "types": stats["types"],
            "liste": [
                {"nom": n["nom"], "type": n.get("type"), "zone": n.get("zone", "")}
                for n in noeuds[:60]
            ],
        }
        return json.dumps(resume, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"erreur": str(e)}, ensure_ascii=False)


@mcp.tool()
def lancer_circuit(nom: str) -> str:
    """Lance un circuit de la carte vivante (ex: "Trouver 712").

    Retourne la décision du routeur (source, message, étapes si c'est un circuit).
    """
    try:
        r = _get_routeur()
        resultat = r.router(f"trouver {nom}")
        rep = {
            "decision": resultat.get("decision"),
            "source": resultat.get("source"),
            "message": resultat.get("message"),
            "resultat": resultat.get("resultat"),
        }
        return json.dumps(rep, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"erreur": str(e)}, ensure_ascii=False)


@mcp.tool()
def demander_alice(message: str) -> str:
    """Passe une demande libre au routeur d'Alice (carte -> memoire -> outils -> modèle)."""
    try:
        r = _get_routeur()
        resultat = r.router(message)
        rep = {
            "decision": resultat.get("decision"),
            "source": resultat.get("source"),
            "message": resultat.get("message") or resultat.get("reponse"),
            "resultat": resultat.get("resultat"),
        }
        return json.dumps(rep, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"erreur": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()