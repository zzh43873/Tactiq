#!/bin/bash
# 地缘政治推演系统 - Lima 启动脚本

set -e

PROJECT_NAME="geopolitical-simulation"
# PROJECT_DIR="$HOME/Applications/geopolitical-simulation"
PROJECT_DIR="/Users/huangyongzhuo/.qoderwork/workspace/mmk7l7pjbb0g7wz4/outputs/geopolitical-simulation"

cd "$PROJECT_DIR"

log_info() { echo "[INFO] $1"; }
log_success() { echo "[SUCCESS] $1"; }
log_warn() { echo "[WARN] $1"; }

# 检查 Lima
check_lima() {
    if ! command -v limactl &> /dev/null; then
        echo "[ERROR] Lima 未安装，请先安装: brew install lima"
        exit 1
    fi
    log_success "Lima 已安装"
}

# 创建 .env 文件
create_env() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_info "创建 .env 配置文件..."
        cat > "$PROJECT_DIR/.env" << 'ENVFILE'
# === 应用配置 ===
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=dev-secret-key-change-in-production

# === 数据库配置 ===
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/geopolitics
DB_HOST=postgres
DB_PORT=5432
DB_USER=user
DB_PASSWORD=password
DB_NAME=geopolitics

# === Redis配置 ===
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379

# === LLM API配置 (必需，请修改为你的密钥) ===
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4-turbo-preview

# === NewsAPI (可选) ===
NEWSAPI_KEY=your-newsapi-key

# === Celery配置 ===
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# === 推演配置 ===
SIMULATION_MAX_ROUNDS=5
SIMULATION_TIMEOUT=300
ENVFILE
        log_warn "请编辑 .env 文件，配置你的 API 密钥"
        log_info "文件位置: $PROJECT_DIR/.env"
    fi
}

# 启动虚拟机
start_vm() {
    log_info "检查虚拟机状态..."
    
    if limactl list "$PROJECT_NAME" --format json 2>/dev/null | grep -q '"status": "Running"'; then
        log_success "虚拟机已在运行"
    elif limactl list "$PROJECT_NAME" 2>/dev/null | grep -q "$PROJECT_NAME"; then
        log_info "启动现有虚拟机..."
        limactl start "$PROJECT_NAME"
    else
        log_info "创建并启动新虚拟机..."
        limactl create --name="$PROJECT_NAME" lima/geopolitical-simulation.yaml
        limactl start "$PROJECT_NAME"
    fi
}

# 启动服务
start_services() {
    log_info "启动 Docker 服务..."
    
    limactl shell "$PROJECT_NAME" << 'LIMACMDS'
        cd /Users/huangyongzhuo/.qoderwork/workspace/mmk7l7pjbb0g7wz4/outputs/geopolitical-simulation
        echo "停止旧服务..."
        docker-compose down 2>/dev/null || true
        echo "启动新服务..."
        docker-compose up -d --build
        echo "等待服务启动..."
        sleep 5
        echo "服务状态:"
        docker-compose ps
LIMACMDS
    
    log_success "服务已启动！"
    echo ""
    echo "访问地址:"
    echo "  - API 文档: http://localhost:8000/docs"
    echo "  - 前端应用: http://localhost:3000"
    echo "  - 健康检查: http://localhost:8000/health"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    limactl shell "$PROJECT_NAME" "cd /Users/huangyongzhuo/.qoderwork/workspace/mmk7l7pjbb0g7wz4/outputs/geopolitical-simulation && docker-compose down" 2>/dev/null || true
    limactl stop "$PROJECT_NAME" 2>/dev/null || true
    log_success "已停止"
}

# 进入 shell
enter_shell() {
    limactl shell "$PROJECT_NAME"
}

# 查看日志
show_logs() {
    log_info "查看服务日志 (按 Ctrl+C 退出)..."
    limactl shell "$PROJECT_NAME" "cd /Users/huangyongzhuo/.qoderwork/workspace/mmk7l7pjbb0g7wz4/outputs/geopolitical-simulation && docker-compose logs -f"
}

# 查看状态
show_status() {
    log_info "虚拟机状态:"
    limactl list "$PROJECT_NAME" 2>/dev/null || log_warn "虚拟机未创建"
    
    echo ""
    log_info "服务状态:"
    limactl shell "$PROJECT_NAME" "cd /Users/huangyongzhuo/.qoderwork/workspace/mmk7l7pjbb0g7wz4/outputs/geopolitical-simulation && docker-compose ps" 2>/dev/null || log_warn "服务未运行"
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            check_lima
            create_env
            start_vm
            start_services
            ;;
        stop)
            stop_services
            ;;
        shell)
            enter_shell
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        *)
            echo "地缘政治推演系统 - Lima 管理脚本"
            echo ""
            echo "用法: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  start    启动虚拟机和所有服务 (默认)"
            echo "  stop     停止服务和虚拟机"
            echo "  shell    进入虚拟机 shell"
            echo "  logs     查看服务日志"
            echo "  status   查看状态"
            echo ""
            echo "示例:"
            echo "  $0 start   # 首次启动"
            echo "  $0 logs    # 查看日志"
            echo "  $0 stop    # 停止服务"
            exit 1
            ;;
    esac
}

main "$@"
