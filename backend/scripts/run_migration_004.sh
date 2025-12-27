#!/bin/bash
# 执行数据库迁移脚本 004_add_intermediate_results_and_views

set -e

echo "=========================================="
echo "执行数据库迁移：004_add_intermediate_results_and_views"
echo "=========================================="

# 检查是否在backend目录
if [ ! -f "alembic.ini" ]; then
    echo "错误：请在backend目录下执行此脚本"
    exit 1
fi

# 检查Docker是否运行
if ! docker ps > /dev/null 2>&1; then
    echo "错误：Docker daemon未运行，请先启动Docker"
    exit 1
fi

# 检查容器是否运行
if ! docker ps | grep -q "it-doc-helper-backend"; then
    echo "警告：backend容器未运行，尝试启动..."
    cd ..
    docker compose up -d backend postgres
    sleep 5
    cd backend
fi

echo ""
echo "步骤1: 检查当前迁移版本..."
docker compose exec backend alembic current || docker-compose exec backend alembic current

echo ""
echo "步骤2: 执行迁移..."
docker compose exec backend alembic upgrade head || docker-compose exec backend alembic upgrade head

echo ""
echo "步骤3: 验证迁移结果..."
docker compose exec backend alembic current || docker-compose exec backend alembic current

echo ""
echo "步骤4: 检查新表..."
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt document_intermediate_results" || \
docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt document_intermediate_results"

echo ""
echo "=========================================="
echo "迁移执行完成！"
echo "=========================================="

