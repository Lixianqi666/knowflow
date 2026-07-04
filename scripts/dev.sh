#!/usr/bin/env bash
# KnowFlow 本地开发环境一键管理脚本
# 用法: ./scripts/dev.sh [start|stop|restart|logs|status|open]
# 不带参数默认 start（后台启动）
set -euo pipefail

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# 红黄绿颜色（终端友好）
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}!${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

ensure_docker() {
  if ! docker info >/dev/null 2>&1; then
    warn "Docker 未运行，正在启动 OrbStack..."
    open -a OrbStack 2>/dev/null || open -a Docker 2>/dev/null || {
      error "未找到 OrbStack 或 Docker，请先安装"; exit 1;
    }
    for i in $(seq 1 12); do
      docker info >/dev/null 2>&1 && break
      echo -n "."; sleep 2
    done
    docker info >/dev/null 2>&1 || { error "Docker 启动超时"; exit 1; }
    echo "" && info "Docker 已就绪"
  fi
}

cmd_start() {
  ensure_docker
  echo -e "${GREEN}▶ 启动 KnowFlow 开发环境...${NC}"
  # 已在运行则提示
  if docker compose $COMPOSE_FILES ps --status running -q 2>/dev/null | grep -q .; then
    warn "已有容器在运行，如需重启请用 ./scripts/dev.sh restart"
  else
    docker compose $COMPOSE_FILES up -d --build 2>&1 | tail -5
  fi
  cmd_status
  echo ""
  info "前端: http://localhost:3000"
  info "后端: http://localhost:8000"
  echo -e "${YELLOW}提示: 首次启动需构建镜像，约 2-5 分钟${NC}"
}

cmd_stop() {
  echo -e "${YELLOW}■ 停止 KnowFlow 开发环境...${NC}"
  docker compose $COMPOSE_FILES down 2>&1 | tail -3
  info "已停止"
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_logs() {
  local svc="${1:-}"
  if [ -n "$svc" ]; then
    docker compose $COMPOSE_FILES logs -f --tail=50 "$svc"
  else
    docker compose $COMPOSE_FILES logs -f --tail=50
  fi
}

cmd_status() {
  echo -e "${GREEN}● 容器状态${NC}"
  docker compose $COMPOSE_FILES ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
}

cmd_open() {
  # 确保 running 后再打开浏览器
  curl -s -o /dev/null http://localhost:3000 && open http://localhost:3000 || {
    warn "前端未就绪，先启动中..."; cmd_start; sleep 2; open http://localhost:3000;
  }
}

case "${1:-start}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_restart ;;
  logs)    shift; cmd_logs "$@" ;;
  status)  cmd_status ;;
  open)    cmd_open ;;
  *) echo "用法: ./scripts/dev.sh [start|stop|restart|logs [服务名]|status|open]"; exit 1 ;;
esac
