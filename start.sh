#!/bin/bash
# Tactiq 启动脚本

echo "=================================="
echo "  Tactiq 地缘政治推演系统"
echo "  新架构版本 (DDD)"
echo "=================================="
echo ""

# 检查环境变量
if [ -f ".env" ]; then
    echo "✓ 找到 .env 配置文件"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠ 未找到 .env 文件，使用默认配置"
fi

# 检查Docker
echo ""
echo "检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo "✗ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "✗ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✓ Docker 环境正常"

# 启动服务
echo ""
echo "启动服务..."
echo ""

cd backend

# 方式1: 使用 Docker Compose (推荐)
echo "方式1: 使用 Docker Compose 启动所有服务"
echo "----------------------------------------"
echo "docker-compose up -d"
echo ""

# 方式2: 本地开发模式
echo "方式2: 本地开发模式 (需要本地 PostgreSQL 和 Redis)"
echo "------------------------------------------------"
echo "1. 确保 PostgreSQL 和 Redis 已启动"
echo "2. 安装依赖: pip install -r requirements.txt"
echo "3. 启动服务: python start.py"
echo ""

# 询问用户选择
echo "请选择启动方式:"
echo "1) Docker Compose (推荐)"
echo "2) 本地开发模式"
echo "3) 仅启动数据库"
echo ""
read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "使用 Docker Compose 启动..."
        cd ..
        docker-compose up -d
        echo ""
        echo "服务已启动:"
        echo "  - API: http://localhost:8000"
        echo "  - 前端: http://localhost:3000"
        echo "  - API文档: http://localhost:8000/docs"
        echo ""
        echo "查看日志: docker-compose logs -f backend"
        ;;
    2)
        echo ""
        echo "本地开发模式..."
        pip install -r requirements.txt
        python start.py
        ;;
    3)
        echo ""
        echo "仅启动数据库..."
        cd ..
        docker-compose up -d postgres redis
        echo ""
        echo "数据库已启动:"
        echo "  - PostgreSQL: localhost:5432"
        echo "  - Redis: localhost:6379"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
