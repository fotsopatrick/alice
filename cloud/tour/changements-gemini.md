# Chloé & Braignak sur Gemini — modifications à rapporter dans ton dépôt
# tour-community (publié sur GitHub) et à activer sur l'instance Cloud Run.

## Fichiers modifiés (2)

- `custom-addons/tour_community_chat/controllers/chat_controller.py`
  - Nouveaux paramètres : `tour_community_chat.provider` (`deepseek` | `gemini`)
    et `tour_community_chat.modele` (défaut `gemini-3.5-flash` côté Gemini).
  - `enregistrer_cle` accepte désormais les clés DeepSeek (`sk-…`) ET Google
    AI Studio (`AIza…` / `AQ.…`) et choisit le fournisseur tout seul.
  - `_chat_local` (ex `_deepseek_local`) branche l'endpoint compatible OpenAI :
    - DeepSeek → `api.deepseek.com/chat/completions`, `max_tokens=3000`
    - Gemini  → `generativelanguage.googleapis.com/v1beta/openai/chat/completions`,
      `max_tokens=12288` (un HTML d'app peut faire ~11k tokens : 3000 tronquait)
  - `DOSSIER_APPS` est paramétrable via `TOUR_APPS_DIR` (Cloud Run : fs en lecture
    seule → `/tmp/community-apps`).
- `custom-addons/tour_community_braignak/controllers/braignak_controller.py`
  - Nouveau paramètre `tour_community_braignak.provider` + détection par clé ;
    modèle par défaut `gemini-3.5-flash` en mode Gemini. Endpoint idem.

Le flux reste OpenAI-compatible (mêmes messages, mêmes `tools`), donc le
fonction-calling de Chloé (construire_app / creer_tache) marche à l'identique
avec Gemini. Comportement validé contre l'API réelle (key `AQ.…`, modèle
`gemini-3.5-flash`) : appel HTTP 200, `tool_calls` → `construire_app`, fichier
`index.html` écrit, boucle arrêtée comme en prod.

## Activation sur l'instance (une fois login admin dans Odoo)

Via Odoo shell (ou Réglages → Paramètres système) :

```python
r = env['ir.config_parameter'].sudo()
r.set_param('tour_community_chat.provider', 'gemini')
r.set_param('tour_community_chat.api_key', '<TA_CLE_AI_STUDIO>')
r.set_param('tour_community_braignak.provider', 'gemini')
r.set_param('tour_community_braignak.api_key', '<TA_CLE_AI_STUDIO>')
```

L'ancienne clé DeepSeek peut rester en place : il suffit de laisser
`provider` vide (vider le paramètre) ou de le mettre à `deepseek`.

## Vérification rapide

1. `/community/chat` → demande à Chloé « construis une page appelée clouddemo ».
2. `curl <URL>/community/app/clouddemo/` → l'HTML doit répondre 200.
3. `/community/braignak` → donne une URL publique à observer.