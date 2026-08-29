#!/usr/bin/env bash
# =====================================================================
# Déploiement Tour Community sur Azure Container Instances (runbook).
#
# IMAGE  : ghcr.io/fotsopatrick/tour-community:latest  (publique, publiée
#          par le workflow GitHub Actions "docker-publish").
#          → Docker Hub fotsopatrick/tour-community:latest si le secret
#            DOCKERHUB_USERNAME/DOCKERHUB_TOKEN est posé sur le dépôt.
#
# PRÉREQUIS (HUMAIN, bloquants) :
#   1. az authentifié : `az login` (console) OU `az login --service-principal
#      -u <CLIENT_ID> -p <CLIENT_SECRET> --tenant <TENANT>` — vérifie
#      `az account show` (exige un tenant réel + une subscription).
#   2. L'image publiée : `curl -sI https://ghcr.io/v2/fotsopatrick/tour-community/manifests/latest`
#      doit répondre 200 (head) une fois le workflow passé.
#
# Variables attendues :
#   AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_LOCATION, AZURE_ACI_NAME,
#   AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY
# =====================================================================
set -euo pipefail

: "${AZURE_SUBSCRIPTION_ID:?exportez-la}"
: "${AZURE_RESOURCE_GROUP:=rg-tour-conquest-20260829}"
: "${AZURE_LOCATION:=eastus}"
: "${AZURE_ACI_NAME:=tour-community-aci}"
: "${AZURE_OPENAI_ENDPOINT:?exportez-le}"
: "${AZURE_OPENAI_KEY:?exportez-la}"
IMAGE="${IMAGE:-ghcr.io/fotsopatrick/tour-community:latest}"

echo "→ Préflight 1/2 — identité Azure…"
az account show --output json >/dev/null ||
  { echo "✗ pas de session az. Action humaine requise : az login (ou SP CI)."; exit 1; }
az account set --subscription "$AZURE_SUBSCRIPTION_ID"

echo "→ Préflight 2/2 — image accessible…"
curl -fsS -o /dev/null -I "https://ghcr.io/v2/fotsopatrick/tour-community/manifests/latest" ||
  { echo "✗ image absente de ghcr.io. Vérifier le workflow Actions, puis re-tenter."; exit 1; }

echo "→ Création du groupe de ressources…"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" --output none

echo "→ Création de l'ACI $AZURE_ACI_NAME…"
az container create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$AZURE_ACI_NAME" \
  --image "$IMAGE" \
  --dns-name-label tour-community-aci \
  --ports 8069 \
  --os-type Linux --cpu 2 --memory 4 \
  --environment-variables \
    AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
    AZURE_OPENAI_KEY="$AZURE_OPENAI_KEY" \
  --output table

URL="http://$(az container show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_ACI_NAME" \
  --query ipAddress.fqdn -o tsv):8069"
echo "✔ Tour en ligne : ${URL}"

echo "→ Validation :"
echo "   $ curl -s -o /dev/null -w '%{http_code}' ${URL}/"
echo "   $ curl -s -o /dev/null -w '%{http_code}' ${URL}/web/login"
echo "   (le dashboard /tour/dashboard + /mcp/tour selon les routes exposées)"