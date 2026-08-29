#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALICE GATE — API :8000
  POST /api/v1/gate   {command, user} -> 202 {job_id, status}
  GET  /api/v1/gate/<job_id>          -> {status, result}
  POST /api/v1/ocr    {image_url}     -> {text}  (200) ou erreur (500)

Reutilise le routeur d'Alice (carte -> memoire -> outils -> modele Qwen).
Les jobs tournent en arriere-plan : le POST repond immediatement (202).
"""
import sys
import time
import json
import uuid
import threading
import tempfile
import os
import urllib.request

sys.path.insert(0, "/home/alice/alicization")
sys.path.insert(0, "/home/alice")

from flask import Flask, request, jsonify
from flask_cors import CORS
from routeur import Routeur, call_model

app = Flask(__name__)
CORS(app)

# Chemins configurables pour le cloud (env) ; par défaut la machine d'Alice.
_CARTE = os.environ.get(
    "ALICE_CARTE", "/home/alice/carte-vivante/cartes.json")
_DB = os.environ.get(
    "ALICE_DB", "/home/alice/alicization/state/alicization.db")

if os.path.dirname(_DB):
    os.makedirs(os.path.dirname(_DB), exist_ok=True)
if not os.path.exists(_CARTE):
    os.makedirs(os.path.dirname(_CARTE), exist_ok=True)
    with open(_CARTE, "w", encoding="utf-8") as _f:
        _f.write('{"zones": []}')

routeur = Routeur(chemin_carte=_CARTE, chemin_db=_DB)

_jobs = {}
_jobs_lock = threading.Lock()

# Réponses brèves et donc rapides sur le moteur Qwen.
SYSTEME_RAPIDE = (
    "Tu es Alice, une assistante IA. Réponds de manière claire et très concise : "
    "une seule phrase, jamais plus de deux."
)


def _creer_job(command):
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "command": command,
                         "created": time.time(), "result": None,
                         "durée_s": None}
    return job_id


def _executer_job(job_id, command):
    t0 = time.time()
    try:
        resultat = routeur.router(command)
        if resultat.get("decision") == "modele":
            # répondre plus court -> plus rapide
            courte = call_model([
                {"role": "system", "content": SYSTEME_RAPIDE},
                {"role": "user", "content": command},
            ], temperature=0.2, max_tokens=128)
            resultat["reponse"] = courte
            resultat["message"] = courte
        payload = {
            "job_id": job_id,
            "decision": resultat.get("decision"),
            "source": resultat.get("source"),
            "message": resultat.get("message") or resultat.get("reponse"),
            "resultat": resultat.get("resultat"),
        }
        etat = "done"
    except Exception as e:
        payload = {"job_id": job_id, "decision": "erreur",
                   "source": "erreur", "message": f"Erreur: {e}"}
        etat = "error"
    with _jobs_lock:
        _jobs[job_id]["status"] = etat
        _jobs[job_id]["result"] = payload
        _jobs[job_id]["durée_s"] = round(time.time() - t0, 3)


@app.route("/api/v1/gate", methods=["POST"])
def gate():
    data = request.get_json(force=True, silent=True) or {}
    command = (data.get("command") or data.get("message") or "").strip()
    user = data.get("user") or "anonyme"
    if not command:
        return jsonify({"error": "champ 'command' manquant"}), 400

    job_id = _creer_job(command)
    threading.Thread(target=_executer_job, args=(job_id, command),
                     daemon=True).start()
    return jsonify({"job_id": job_id, "status": "running",
                    "message": f"demande reçue de {user}"}), 202


@app.route("/api/v1/gate/<job_id>", methods=["GET"])
def gate_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "job inconnu"}), 404
    rep = {"job_id": job_id, "status": job["status"],
           "durée_s": job["durée_s"]}
    if job["result"] is not None:
        rep["result"] = job["result"]
    return jsonify(rep), (200 if job["status"] != "error" else 500)


@app.route("/api/v1/ocr", methods=["POST"])
def ocr():
    """Lis une image distante (image_url) avec Tesseract."""
    data = request.get_json(force=True, silent=True) or {}
    image_url = data.get("image_url") or data.get("url") or ""
    if not image_url:
        return jsonify({"error": "champ 'image_url' manquant"}), 400

    try:
        suffix = os.path.splitext(urllib.request.urlparse(image_url).path)[1] or ".png"
        if suffix.lower() not in (".png", ".jpg", ".jpeg", ".ppm", ".pgm", ".bmp", ".tif", ".tiff", ".webp"):
            suffix = ".png"
        tmp_path = tempfile.mktemp(suffix=suffix)
        try:
            with urllib.request.urlopen(image_url, timeout=10) as r:
                contenu = r.read()
        except Exception as e:
            return jsonify({"error": f"telechargement image: {e}"}), 500
        with open(tmp_path, "wb") as f:
            f.write(contenu)
        try:
            from outils.ocr import extraire_texte
        except ImportError:
            return jsonify({"error": "outil OCR introuvable"}), 500
        texte = extraire_texte(tmp_path)
        if texte:
            return jsonify({"text": texte, "source": image_url}), 200
        return jsonify({"error": "rien lu dans l'image",
                        "source": image_url}), 500
    except Exception as e:
        return jsonify({"error": f"OCR échoué: {e}"}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "alice-gate"})


@app.route("/", methods=["GET"])
def index():
    return jsonify({"usage": "POST /api/v1/gate {command} ; GET /api/v1/gate/<id> ; POST /api/v1/ocr {image_url}"})


if __name__ == "__main__":
    try:
        os.makedirs("/home/alice/alicization/logs", exist_ok=True)
    except Exception:
        pass
    app.run(host="0.0.0.0", port=8000, threaded=True)