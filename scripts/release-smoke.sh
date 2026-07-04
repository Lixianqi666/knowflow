#!/bin/sh
# 发布后 Smoke Test
set -eu

echo "=== KnowFlow Smoke Test ==="

PASS=0
FAIL=0

# 检查 docker compose ps
echo -n "检查服务状态... "
if docker compose ps --format '{{.Name}} {{.Status}}' 2>/dev/null | grep -q "Up"; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

# 检查后端健康
echo -n "检查后端健康... "
if curl -sf http://127.0.0.1/health >/dev/null 2>&1; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

# 检查前端可访问
echo -n "检查前端可访问... "
if curl -sf http://127.0.0.1/ >/dev/null 2>&1; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

# 检查后端 API
echo -n "检查后端 API... "
RESP=$(curl -sf http://127.0.0.1/api/v1/auth/sso/providers 2>/dev/null || echo "")
if echo "${RESP}" | grep -q "oidc"; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== 结果: ${PASS} 通过, ${FAIL} 失败 ==="

if [ "${FAIL}" -gt 0 ]; then
  exit 1
fi
