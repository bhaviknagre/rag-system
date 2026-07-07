GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN} PASS${NC} $1"; }
fail() { echo -e "${RED} FAIL${NC} $1"; }
warn() { echo -e "${YELLOW}  WARN${NC} $1"; }

echo "=== RAG System Health Check ==="
echo ""

# Nginx
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/nginx-health 2>/dev/null)
[ "$STATUS" = "200" ] && pass "Nginx (port 80)" || fail "Nginx (port 80) — got HTTP $STATUS"

# API via Nginx
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null)
[ "$STATUS" = "200" ] && pass "API via Nginx (http://localhost/health)" || fail "API via Nginx — got HTTP $STATUS"

# Prometheus
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090/-/healthy 2>/dev/null)
[ "$STATUS" = "200" ] && pass "Prometheus (port 9090)" || fail "Prometheus — got HTTP $STATUS"

# Grafana
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null)
[ "$STATUS" = "200" ] && pass "Grafana (port 3000)" || fail "Grafana — got HTTP $STATUS"

# Flower
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5555 2>/dev/null)
[ "$STATUS" = "200" ] && pass "Flower (port 5555)" || fail "Flower — got HTTP $STATUS"

# Redis
docker exec rag-redis redis-cli ping 2>/dev/null | grep -q PONG \
  && pass "Redis (port 6379)" || fail "Redis"

# API metrics endpoint
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090/metrics 2>/dev/null)
[ "$STATUS" = "200" ] && pass "Prometheus metrics scraping" || warn "Prometheus metrics — check targets at http://localhost:9090/targets"

echo ""
echo "=== API Health Detail ==="
curl -s http://localhost/health | python3 -m json.tool 2>/dev/null || echo "Could not reach API"

echo ""
echo "=== Instance Counts ==="
bash scripts/scale.sh status