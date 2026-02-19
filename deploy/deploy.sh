#!/usr/bin/env bash
# Build, push, and deploy a new image to Azure Container Apps.
# Requires: Docker, az CLI logged in, environment variables below set.
#
# Usage:
#   ACR_NAME=verkiezingacr \
#   CONTAINER_APP_NAME=verkiezing-app \
#   CONTAINER_APP_RG=verkiezing-rg \
#   ./deploy/deploy.sh

set -euo pipefail

ACR_NAME="${ACR_NAME:?Set ACR_NAME}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:?Set CONTAINER_APP_NAME}"
CONTAINER_APP_RG="${CONTAINER_APP_RG:?Set CONTAINER_APP_RG}"
IMAGE_NAME="verkiezing-vibecheck"

ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
TAG="${1:-$(git rev-parse --short HEAD)}"
FULL_IMAGE="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${TAG}"

echo "==> Logging into ACR"
az acr login --name "$ACR_NAME"

echo "==> Building image: $FULL_IMAGE"
docker build --platform linux/amd64 -t "$FULL_IMAGE" -t "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" .

echo "==> Pushing image"
docker push "$FULL_IMAGE"
docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"

echo "==> Updating Container App"
az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$CONTAINER_APP_RG" \
  --image "$FULL_IMAGE"

echo ""
echo "✓ Deployed $FULL_IMAGE"
