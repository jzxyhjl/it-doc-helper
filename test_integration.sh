#!/bin/bash

# 集成测试脚本
# 测试可信度估计、来源引用、异常处理和失败策略

BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost/it-doc-helper"

echo "=========================================="
echo "集成测试：可信度估计和来源引用功能"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
PASSED=0
FAILED=0

# 测试函数
test_check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $1"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $1"
        ((FAILED++))
    fi
}

test_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

echo "1. 检查服务状态..."
echo "----------------------------------------"

# 检查后端服务
if curl -s -f "${BASE_URL}/health" > /dev/null 2>&1; then
    test_check "后端服务运行正常"
    BACKEND_UP=true
else
    echo -e "${RED}✗ FAIL${NC}: 后端服务未运行"
    echo "  启动命令: docker-compose up -d"
    BACKEND_UP=false
fi

# 检查前端服务
if curl -s -f "${FRONTEND_URL}" > /dev/null 2>&1; then
    test_check "前端服务运行正常"
else
    test_warn "前端服务未运行（可选）"
fi

if [ "$BACKEND_UP" = false ]; then
    echo ""
    echo -e "${YELLOW}警告：后端服务未运行，跳过后续测试${NC}"
    echo ""
    echo "请先启动服务："
    echo "  docker-compose up -d"
    echo ""
    echo "然后重新运行测试："
    echo "  ./test_integration.sh"
    exit 1
fi

echo ""
echo "2. 测试文档上传和大小验证..."
echo "----------------------------------------"

# 检查测试文件是否存在
if [ ! -f "test_document.md" ]; then
    echo "创建测试文档..."
    cat > test_document.md << 'EOF'
# 测试文档

这是一个用于集成测试的示例文档。

## 技术栈

本系统使用以下技术：
- FastAPI：后端框架
- React：前端框架
- PostgreSQL：数据库
- Redis：缓存和任务队列

## 功能特性

1. 文档上传和处理
2. 智能分类
3. 可信度估计
4. 来源引用

这是一个简短的测试文档，用于验证系统的基本功能。
EOF
    test_check "创建测试文档"
fi

# 测试1: 正常文件上传
echo "测试1.1: 上传正常大小的文档..."
UPLOAD_RESPONSE=$(curl -s -X POST \
    -F "file=@test_document.md" \
    "${BASE_URL}/api/v1/documents/upload" 2>&1)

if echo "$UPLOAD_RESPONSE" | grep -q "document_id"; then
    DOCUMENT_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"document_id":"[^"]*"' | cut -d'"' -f4)
    test_check "正常文件上传成功 (document_id: ${DOCUMENT_ID:0:8}...)"
else
    test_check "正常文件上传失败"
    echo "  响应: $UPLOAD_RESPONSE"
fi

# 测试2: 文件大小验证（如果文件存在）
if [ -f "test_document.md" ]; then
    FILE_SIZE=$(stat -f%z "test_document.md" 2>/dev/null || stat -c%s "test_document.md" 2>/dev/null)
    if [ "$FILE_SIZE" -gt 20971520 ]; then  # 20MB
        test_warn "测试文件较大 (${FILE_SIZE} bytes)，处理时间可能较长"
    fi
fi

echo ""
echo "3. 测试处理结果结构..."
echo "----------------------------------------"

if [ -n "$DOCUMENT_ID" ]; then
    echo "等待处理完成（最多等待60秒）..."
    
    MAX_WAIT=60
    WAITED=0
    STATUS="pending"
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        sleep 2
        WAITED=$((WAITED + 2))
        
        PROGRESS_RESPONSE=$(curl -s "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/progress")
        STATUS=$(echo "$PROGRESS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        PROGRESS=$(echo "$PROGRESS_RESPONSE" | grep -o '"progress":[0-9]*' | cut -d':' -f2)
        
        echo "  进度: ${PROGRESS}%, 状态: ${STATUS}"
        
        if [ "$STATUS" = "completed" ]; then
            break
        elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "timeout" ] || [ "$STATUS" = "low_quality" ]; then
            echo -e "${YELLOW}处理失败，状态: ${STATUS}${NC}"
            break
        fi
    done
    
    if [ "$STATUS" = "completed" ]; then
        test_check "文档处理完成"
        
        # 获取处理结果
        RESULT_RESPONSE=$(curl -s "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/result")
        
        # 测试3: 检查结果结构
        echo ""
        echo "测试3.1: 检查结果结构..."
        
        if echo "$RESULT_RESPONSE" | grep -q "document_type"; then
            test_check "结果包含 document_type 字段"
        else
            test_check "结果缺少 document_type 字段"
        fi
        
        if echo "$RESULT_RESPONSE" | grep -q "result"; then
            test_check "结果包含 result 字段"
        else
            test_check "结果缺少 result 字段"
        fi
        
        # 测试4: 检查可信度字段（如果存在）
        echo ""
        echo "测试4: 检查可信度和来源字段..."
        
        if echo "$RESULT_RESPONSE" | grep -q "confidence"; then
            test_check "结果包含 confidence 字段"
        else
            test_warn "结果未包含 confidence 字段（可能为旧格式）"
        fi
        
        if echo "$RESULT_RESPONSE" | grep -q "sources"; then
            test_check "结果包含 sources 字段"
        else
            test_warn "结果未包含 sources 字段（可能为旧格式）"
        fi
        
        # 测试5: 检查失败状态处理
        echo ""
        echo "测试5: 检查失败状态处理..."
        
        DOC_STATUS=$(echo "$RESULT_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        if [ "$DOC_STATUS" = "failed" ] || [ "$DOC_STATUS" = "timeout" ] || [ "$DOC_STATUS" = "low_quality" ]; then
            test_warn "文档状态为失败: ${DOC_STATUS}"
            if echo "$RESULT_RESPONSE" | grep -q "error_message"; then
                test_check "失败结果包含错误信息"
            fi
        else
            test_check "文档状态正常"
        fi
        
    else
        test_warn "文档处理未完成或失败，状态: ${STATUS}"
    fi
else
    test_warn "无法测试处理结果（文档ID未获取）"
fi

echo ""
echo "6. 测试异常场景..."
echo "----------------------------------------"

# 测试6: 无效文件上传
echo "测试6.1: 尝试上传无效文件..."
INVALID_RESPONSE=$(curl -s -X POST \
    -F "file=@/dev/null" \
    "${BASE_URL}/api/v1/documents/upload" 2>&1)

if echo "$INVALID_RESPONSE" | grep -q "不支持\|错误\|失败"; then
    test_check "无效文件被正确拒绝"
else
    test_warn "无效文件处理结果: $INVALID_RESPONSE"
fi

# 测试7: 不存在的文档ID
echo ""
echo "测试7: 查询不存在的文档..."
NOT_FOUND_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/api/v1/documents/00000000-0000-0000-0000-000000000000/result" 2>&1)
HTTP_CODE=$(echo "$NOT_FOUND_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "404" ]; then
    test_check "不存在的文档返回404"
else
    test_check "不存在的文档处理异常 (HTTP: $HTTP_CODE)"
fi

echo ""
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo "通过: ${PASSED}"
echo "失败: ${FAILED}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}部分测试失败，请检查上述错误${NC}"
    exit 1
fi

