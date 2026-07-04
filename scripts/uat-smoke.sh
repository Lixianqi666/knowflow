#!/bin/sh
# UAT 交付材料检查脚本
set -eu

echo "=== KnowFlow UAT Smoke Check ==="

PASS=0
FAIL=0

# 检查 VERSION
echo -n "VERSION 文件... "
if [ -f "VERSION" ] && [ -s "VERSION" ]; then
  echo "OK ($(cat VERSION))"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

# 检查 CHANGELOG
echo -n "CHANGELOG.md... "
if [ -f "CHANGELOG.md" ] && [ -s "CHANGELOG.md" ]; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

# 检查 release manifest
echo -n "dist/release-manifest.json... "
if [ -f "dist/release-manifest.json" ]; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "MISSING (run: bash scripts/build-release-manifest.sh)"
  FAIL=$((FAIL + 1))
fi

# 检查 UAT 文档
for doc in docs/uat_checklist.md docs/acceptance_report_template.md docs/production_readiness.md docs/delivery_package.md docs/versioning.md; do
  echo -n "${doc}... "
  if [ -f "${doc}" ]; then
    echo "OK"
    PASS=$((PASS + 1))
  else
    echo "FAIL"
    FAIL=$((FAIL + 1))
  fi
done

# 检查 docker compose 配置
echo -n "docker compose config... "
if docker compose config --quiet 2>/dev/null; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "FAIL"
  FAIL=$((FAIL + 1))
fi

# 检查 Dockerfiles
for f in backend/Dockerfile frontend/Dockerfile; do
  echo -n "${f}... "
  if [ -f "${f}" ]; then
    echo "OK"
    PASS=$((PASS + 1))
  else
    echo "FAIL"
    FAIL=$((FAIL + 1))
  fi
done

# 检查运维脚本
for s in scripts/preflight-docker.sh scripts/backup-db.sh scripts/restore-db.sh scripts/release-smoke.sh scripts/verify-docker.sh; do
  echo -n "${s}... "
  if [ -f "${s}" ]; then
    echo "OK"
    PASS=$((PASS + 1))
  else
    echo "FAIL"
    FAIL=$((FAIL + 1))
  fi
done

# 可选：如果服务已启动，检查健康
echo -n "Health check (optional)... "
if curl -sf http://127.0.0.1/health >/dev/null 2>&1; then
  echo "OK"
  PASS=$((PASS + 1))
else
  echo "SKIPPED (service not running)"
fi

echo ""
echo "=== 结果: ${PASS} 通过, ${FAIL} 失败 ==="

if [ "${FAIL}" -gt 0 ]; then
  exit 1
fi
