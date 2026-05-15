#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="rentmanager"

echo "Applying k8s manifests..."
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/rbac.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/secrets.yml
kubectl apply -f k8s/network-policies.yml
kubectl apply -f k8s/postgres.yml
kubectl apply -f k8s/redis.yml
kubectl apply -f k8s/meilisearch.yml
kubectl apply -f k8s/minio.yml

echo "Waiting for data services..."
kubectl rollout status statefulset/postgres -n $NAMESPACE --timeout=120s
kubectl rollout status statefulset/redis -n $NAMESPACE --timeout=60s
kubectl rollout status statefulset/meilisearch -n $NAMESPACE --timeout=60s
kubectl rollout status statefulset/minio -n $NAMESPACE --timeout=60s

echo "Deploying application..."
kubectl apply -f k8s/backend.yml
kubectl apply -f k8s/celery.yml
kubectl apply -f k8s/frontend.yml
kubectl apply -f k8s/ingress.yml

echo "Waiting for rollout..."
kubectl rollout status deployment/backend -n $NAMESPACE --timeout=120s
kubectl rollout status deployment/frontend -n $NAMESPACE --timeout=120s

echo "Deploy complete!"
kubectl get pods -n $NAMESPACE
