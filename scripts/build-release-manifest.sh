#!/bin/sh
# 构建发布清单
set -eu

VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
else
  GIT_COMMIT="unknown"
fi

mkdir -p dist

cat > dist/release-manifest.json << EOF
{
  "version": "${VERSION}",
  "generated_at": "${GENERATED_AT}",
  "git_commit": "${GIT_COMMIT}",
  "files": {
    "compose": "docker-compose.yml",
    "backend_dockerfile": "backend/Dockerfile",
    "frontend_dockerfile": "frontend/Dockerfile",
    "env_example": ".env.example"
  },
  "docs": [
    "README.md",
    "CHANGELOG.md",
    "VERSION",
    "docs/private_deployment.md",
    "docs/upgrade_rollback.md",
    "docs/backup_restore.md",
    "docs/release_checklist.md",
    "docs/delivery_package.md",
    "docs/versioning.md"
  ],
  "scripts": [
    "scripts/preflight-docker.sh",
    "scripts/backup-db.sh",
    "scripts/restore-db.sh",
    "scripts/release-smoke.sh",
    "scripts/verify-docker.sh",
    "scripts/print-version.sh",
    "scripts/build-release-manifest.sh"
  ]
}
EOF

echo "Release manifest generated: dist/release-manifest.json"
