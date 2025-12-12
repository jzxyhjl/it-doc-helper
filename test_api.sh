#!/bin/bash

echo "=== IT学习辅助系统 API 测试 ==="
echo ""

# 测试健康检查
echo "1. 测试健康检查..."
curl -s http://localhost:8000/health | jq . || echo "健康检查失败"
echo ""

# 测试根路径
echo "2. 测试根路径..."
curl -s http://localhost:8000/ | jq . || echo "根路径测试失败"
echo ""

# 测试API文档
echo "3. 检查API文档..."
echo "API文档地址: http://localhost:8000/docs"
echo ""

# 测试前端
echo "4. 测试前端..."
curl -s -I http://localhost/it-doc-helper/ | head -5
echo ""

echo "=== 测试完成 ==="
echo ""
echo "访问地址:"
echo "  前端: http://localhost/it-doc-helper"
echo "  API文档: http://localhost:8000/docs"
echo "  API健康检查: http://localhost:8000/health"

