#!/bin/bash
set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER:-desktop}"
NAMESPACE="rentmanager"

echo "==> Building images..."
docker build -t rentmanager-backend:latest --target prod backend/
docker build -t rentmanager-frontend:latest --target prod frontend/

echo "==> Loading images into Kind cluster '$CLUSTER_NAME'..."
kind load docker-image rentmanager-backend:latest --name "$CLUSTER_NAME"
kind load docker-image rentmanager-frontend:latest --name "$CLUSTER_NAME"

echo "==> Installing nginx-ingress (if not present)..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml 2>/dev/null || true
echo "    Waiting for ingress controller..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s 2>/dev/null || echo "    (ingress controller may already be ready)"

echo "==> Applying K8s manifests..."
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/rbac.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/secrets.yml
kubectl apply -f k8s/network-policies.yml
kubectl apply -f k8s/postgres.yml
kubectl apply -f k8s/redis.yml
kubectl apply -f k8s/meilisearch.yml
kubectl apply -f k8s/minio.yml

echo "==> Waiting for data services..."
kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=120s
kubectl rollout status statefulset/redis -n "$NAMESPACE" --timeout=60s
kubectl rollout status statefulset/meilisearch -n "$NAMESPACE" --timeout=60s
kubectl rollout status statefulset/minio -n "$NAMESPACE" --timeout=60s

echo "==> Deploying application..."
kubectl apply -f k8s/backend.yml
kubectl apply -f k8s/celery.yml
kubectl apply -f k8s/frontend.yml
kubectl apply -f k8s/ingress.yml

echo "==> Waiting for rollouts..."
kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=120s
kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=120s

echo ""
echo "==> Done! Pods:"
kubectl get pods -n "$NAMESPACE"
echo ""
echo "==> Services:"
kubectl get svc -n "$NAMESPACE"
echo ""
echo "Access via port-forward:"
echo "  kubectl port-forward svc/frontend 3000:3000 -n $NAMESPACE"
echo "  kubectl port-forward svc/backend 8000:8000 -n $NAMESPACE"
