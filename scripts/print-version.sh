#!/bin/sh
# 打印版本信息
set -eu

VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

echo "KnowFlow version: ${VERSION}"

# Git commit
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  echo "Git commit: ${COMMIT}"
else
  echo "Git commit: unknown"
fi

# Docker Compose
if docker compose config --quiet 2>/dev/null; then
  echo "Docker Compose: valid"
else
  echo "Docker Compose: invalid or not available"
fi

# Dockerfiles
if [ -f "backend/Dockerfile" ]; then
  echo "Backend Dockerfile: exists"
else
  echo "Backend Dockerfile: missing"
fi

if [ -f "frontend/Dockerfile" ]; then
  echo "Frontend Dockerfile: exists"
else
  echo "Frontend Dockerfile: missing"
fi
