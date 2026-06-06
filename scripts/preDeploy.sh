#!/usr/bin/env bash
set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────
CLUSTER_NAME="rentmanager"
NAMESPACE="rentmanager"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K8S_DIR="$PROJECT_ROOT/k8s"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
step()  { echo; echo -e "${BLUE}━━━ $* ━━━${NC}"; }

# ─── Preflight ───────────────────────────────────────────────────
step "Preflight checks"

# Detect OS
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
esac

LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"
mkdir -p "$LOCAL_BIN"

install_kind() {
  warn "Installing kind to $LOCAL_BIN..."
  if [ "$OS" = "darwin" ] && command -v brew &>/dev/null && [ -w "$(brew --prefix)" ]; then
    brew install kind
  else
    local url="https://kind.sigs.k8s.io/dl/latest/kind-${OS}-${ARCH}"
    curl -fsSL "$url" -o "$LOCAL_BIN/kind"
    chmod +x "$LOCAL_BIN/kind"
  fi
  ok "kind installed ($(kind version 2>/dev/null || echo "add $LOCAL_BIN to your PATH"))"
}

install_kubectl() {
  warn "Installing kubectl to $LOCAL_BIN..."
  if [ "$OS" = "darwin" ] && command -v brew &>/dev/null && [ -w "$(brew --prefix)" ]; then
    brew install kubectl
  else
    LATEST="$(curl -fsL https://dl.k8s.io/release/stable.txt)"
    local url="https://dl.k8s.io/release/${LATEST}/bin/${OS}/${ARCH}/kubectl"
    curl -fsSL "$url" -o "$LOCAL_BIN/kubectl"
    chmod +x "$LOCAL_BIN/kubectl"
  fi
  ok "kubectl installed ($(kubectl version --client 2>/dev/null | head -1 || echo "add $LOCAL_BIN to your PATH"))"
}

command -v kind &>/dev/null || install_kind
command -v kubectl &>/dev/null || install_kubectl

install_docker() {
  warn "Installing Docker..."
  if [ "$OS" = "darwin" ]; then
    fail "Docker not found. Install Docker Desktop manually from https://docs.docker.com/get-docker/"
  else
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker "$(whoami)" 2>/dev/null || true
    rm -f /tmp/get-docker.sh
    ok "Docker installed — you may need to log out/back in for group changes"
  fi
}
command -v docker &>/dev/null || install_docker

if ! docker info &>/dev/null; then
  if [ "$OS" != "darwin" ]; then
    warn "Docker daemon not running — attempting to start..."
    sudo systemctl start docker 2>/dev/null || sudo dockerd &>/tmp/dockerd.log &
    sleep 5
  fi
  if ! docker info &>/dev/null; then
    sudo docker info &>/dev/null || \
      fail "Docker daemon is not running. Start it (e.g., sudo systemctl start docker)."
    warn "Docker requires sudo — adding user to docker group..."
    sudo usermod -aG docker "$(whoami)"
    fail "Added $(whoami) to docker group. Log out and back in, then re-run this script."
  fi
fi

ok "All prerequisites satisfied"

# ─── Kind cluster ─────────────────────────────────────────────────
step "Kind cluster: $CLUSTER_NAME"

if kind get clusters 2>/dev/null | grep -q "^$CLUSTER_NAME$"; then
  warn "Cluster '$CLUSTER_NAME' already exists — skipping creation"
else
  # Only check port 80 when creating a new cluster (existing cluster owns it)
  if lsof -i :80 -P -n 2>/dev/null | grep -q LISTEN; then
    fail "Port 80 is already in use (not by our cluster). Free it first."
  fi
  info "Creating cluster with port 80/443 mapping..."
  cat > /tmp/kind-rm-config.yml <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $CLUSTER_NAME
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
  kind create cluster --config /tmp/kind-rm-config.yml
  rm -f /tmp/kind-rm-config.yml
  ok "Cluster created"
fi

# Set context
kubectl config use-context "kind-$CLUSTER_NAME" 2>/dev/null || true

# ─── Build images ─────────────────────────────────────────────────
step "Build Docker images"
info "Building backend (prod target)..."
docker build -t rentmanager-backend:latest --target prod "$PROJECT_ROOT/backend"
ok "Backend image built"

info "Building frontend (prod target)..."
docker build -t rentmanager-frontend:latest --target prod "$PROJECT_ROOT/frontend"
ok "Frontend image built"

# ─── Load images into Kind ───────────────────────────────────────
step "Load images into Kind cluster"
kind load docker-image rentmanager-backend:latest --name "$CLUSTER_NAME"
kind load docker-image rentmanager-frontend:latest --name "$CLUSTER_NAME"
ok "Images loaded"

# ─── Install ingress-nginx ────────────────────────────────────────
step "Install ingress-nginx"
INGRESS_URL="https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"
kubectl apply -f "$INGRESS_URL" 2>/dev/null || true
info "Waiting for ingress controller..."
sleep 5
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
ok "ingress-nginx ready"

# ─── Apply infra manifests ───────────────────────────────────────
step "Deploy infrastructure (Postgres, Redis, Meilisearch, MinIO)"

for f in namespace.yml rbac.yml configmap.yml secrets.yml network-policies.yml \
         postgres.yml redis.yml meilisearch.yml minio.yml; do
  info "Applying $f..."
  kubectl apply -f "$K8S_DIR/$f"
done

info "Waiting for Postgres..."
kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=180s
info "Waiting for Redis..."
kubectl rollout status statefulset/redis -n "$NAMESPACE" --timeout=120s
info "Waiting for Meilisearch..."
kubectl rollout status statefulset/meilisearch -n "$NAMESPACE" --timeout=120s
info "Waiting for MinIO..."
kubectl rollout status statefulset/minio -n "$NAMESPACE" --timeout=120s
ok "All data services ready"

# ─── Apply app manifests ─────────────────────────────────────────
step "Deploy application (Backend, Celery, Frontend)"

for f in backend.yml celery.yml frontend.yml ingress.yml; do
  info "Applying $f..."
  kubectl apply -f "$K8S_DIR/$f"
done

# Force restart so all pods pick up the freshly loaded images
# (works on fresh deploy too — pods don't exist yet, restart is a no-op)
step "Restarting deployments to pick up fresh images"
for deploy in backend celery-worker celery-beat frontend; do
  if kubectl get deployment "$deploy" -n "$NAMESPACE" &>/dev/null; then
    kubectl rollout restart "deployment/$deploy" -n "$NAMESPACE"
  fi
done

info "Waiting for Backend..."
kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=300s
info "Waiting for Celery worker..."
kubectl rollout status deployment/celery-worker -n "$NAMESPACE" --timeout=180s
info "Waiting for Frontend..."
kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=180s
ok "All application pods ready"

# ─── Run seed data ────────────────────────────────────────────────
step "Seed data"
SEED_POD=$(kubectl get pod -n "$NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [ -n "$SEED_POD" ]; then
  info "Running seed_demo..."
  kubectl exec -n "$NAMESPACE" "$SEED_POD" -- python -m scripts.seed_demo 2>/dev/null && \
    ok "seed_demo complete" || warn "seed_demo skipped (may already be seeded)"
  info "Running seed_addons..."
  kubectl exec -n "$NAMESPACE" "$SEED_POD" -- python -m scripts.seed_addons 2>/dev/null && \
    ok "seed_addons complete" || warn "seed_addons skipped (may already be seeded)"
else
  warn "No backend pod found for seeding — do it manually later"
fi

# ─── Summary ──────────────────────────────────────────────────────
step "Deployment summary"
echo ""
kubectl get pods -n "$NAMESPACE" -o wide
echo ""
kubectl get svc -n "$NAMESPACE"
echo ""
echo -e "${GREEN}━━━ RentManager is live! ━━━${NC}"
echo -e "  Frontend:  ${BLUE}http://localhost${NC}"
echo -e "  Backend:   ${BLUE}http://localhost/api${NC}"
echo -e "  Health:    ${BLUE}http://localhost/api/health${NC}"
echo ""
echo -e "  To tear down:  ${YELLOW}kind delete cluster --name $CLUSTER_NAME${NC}"
echo -e "  To stop:       ${YELLOW}kind get nodes --name $CLUSTER_NAME | xargs docker stop${NC}"
echo -e "  To restart:    ${YELLOW}kind get nodes --name $CLUSTER_NAME | xargs docker start${NC}"
echo ""
