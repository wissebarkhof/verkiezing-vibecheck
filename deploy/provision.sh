#!/usr/bin/env bash
# Provision all Azure resources for verkiezing-vibecheck.
# Run once. Requires: az CLI logged in, a subscription set.
#
# Usage:
#   chmod +x deploy/provision.sh
#   ./deploy/provision.sh
#
# After running, copy the printed environment variables into your
# GitHub repository secrets (Settings → Secrets → Actions).

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
RESOURCE_GROUP="verkiezing-rg"
LOCATION="westeurope"
ACR_NAME="verkiezingacr"            # must be globally unique, lowercase, alphanumeric
POSTGRES_SERVER="verkiezing-pg"     # must be globally unique
POSTGRES_DB="verkiezing"
POSTGRES_USER="pgadmin"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -base64 24)}"
CONTAINER_APP_ENV="verkiezing-env"
CONTAINER_APP_NAME="verkiezing-app"
IMAGE_NAME="verkiezing-vibecheck"
# ─────────────────────────────────────────────────────────────────────────────

echo "==> Creating resource group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "==> Creating Azure Container Registry: $ACR_NAME"
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

echo "==> Creating PostgreSQL Flexible Server: $POSTGRES_SERVER"
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER" \
  --location "$LOCATION" \
  --admin-user "$POSTGRES_USER" \
  --admin-password "$POSTGRES_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0

echo "==> Creating database: $POSTGRES_DB"
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER" \
  --database-name "$POSTGRES_DB"

echo "==> Enabling pgvector extension"
az postgres flexible-server parameter set \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER" \
  --name azure.extensions \
  --value vector

POSTGRES_HOST=$(az postgres flexible-server show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER" \
  --query fullyQualifiedDomainName -o tsv)

DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}?sslmode=require"

echo "==> Creating Container Apps environment: $CONTAINER_APP_ENV"
az containerapp env create \
  --name "$CONTAINER_APP_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

echo "==> Creating Container App: $CONTAINER_APP_NAME"
az containerapp create \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_APP_ENV" \
  --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASSWORD" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --env-vars \
      DATABASE_URL="$DATABASE_URL" \
      ENVIRONMENT=production \
      ELECTION_CONFIG=data/elections/amsterdam-2026.yml \
      ANTHROPIC_API_KEY=secretref:anthropic-key \
      OPENAI_API_KEY=secretref:openai-key \
  --secrets \
      anthropic-key="${ANTHROPIC_API_KEY:-changeme}" \
      openai-key="${OPENAI_API_KEY:-changeme}"

APP_URL=$(az containerapp show \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "✓ Provisioning complete!"
echo ""
echo "App URL: https://$APP_URL"
echo ""
echo "Add these secrets to GitHub Actions (Settings → Secrets → Actions):"
echo "  AZURE_CREDENTIALS      → output of: az ad sp create-for-rbac --sdk-auth"
echo "  ACR_NAME               → $ACR_NAME"
echo "  ACR_LOGIN_SERVER       → $ACR_LOGIN_SERVER"
echo "  ACR_PASSWORD           → $ACR_PASSWORD"
echo "  CONTAINER_APP_NAME     → $CONTAINER_APP_NAME"
echo "  CONTAINER_APP_RG       → $RESOURCE_GROUP"
echo "  DATABASE_URL           → $DATABASE_URL"
echo "  ANTHROPIC_API_KEY      → (your key)"
echo "  OPENAI_API_KEY         → (your key)"
