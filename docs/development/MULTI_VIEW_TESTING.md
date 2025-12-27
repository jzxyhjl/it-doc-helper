# 多视角处理逻辑测试文档

## 测试概述

本文档描述了多视角处理逻辑的测试用例，验证系统能够正确处理多个视角的文档处理。

## 测试文件

**文件位置**：`backend/tests/test_regression/test_multi_view_processing.py`

## 测试分类

### 1. 视角识别和推荐测试 (`TestViewClassification`)

测试视角分类器的功能：

- **test_detect_qa_structure**: 测试Q&A结构检测
- **test_detect_component_relationships**: 测试系统组件关系检测
- **test_detect_usage_flow**: 测试使用流程检测
- **test_recommend_views_technical_document**: 测试技术文档的视角推荐
- **test_recommend_views_interview_document**: 测试面试题文档的视角推荐
- **test_recommend_views_architecture_document**: 测试架构文档的视角推荐
- **test_recommend_views_multi_perspective**: 测试多视角文档的推荐
- **test_generate_cache_key_from_scores**: 测试基于检测得分生成缓存key

### 2. 视角注册表测试 (`TestViewRegistry`)

测试视角注册表的功能：

- **test_view_registry_registration**: 测试视角注册
- **test_get_processor**: 测试获取处理器
- **test_get_type_mapping**: 测试类型映射（向后兼容）
- **test_get_view_from_type**: 测试从类型推断视角（向后兼容）
- **test_get_display_name**: 测试获取显示名称

### 3. 多视角输出容器测试 (`TestMultiViewContainer`)

测试多视角输出容器的功能：

- **test_create_container**: 测试创建容器
- **test_get_view**: 测试获取视角结果
- **test_has_view**: 测试检查视角是否存在
- **test_list_views**: 测试列出所有视角
- **test_get_primary_view**: 测试获取主视角
- **test_get_enabled_views**: 测试获取启用的视角列表
- **test_get_confidence**: 测试获取置信度

### 4. 视角处理逻辑测试 (`TestViewProcessing`)

测试视角处理的核心逻辑：

- **test_process_view_independently**: 测试独立处理单个视角（难点1：多视角独立性）
- **test_process_views_with_priority**: 测试主次视角优先级处理（难点4）

### 5. 中间结果复用测试 (`TestIntermediateResults`)

测试中间结果的视角无关性：

- **test_save_and_retrieve_intermediate_results**: 测试保存和检索中间结果
- **test_intermediate_results_view_agnostic**: 测试中间结果视角无关性（难点3）

## 运行测试

### 运行所有多视角测试

```bash
docker exec it-doc-helper-backend pytest tests/test_regression/test_multi_view_processing.py -v
```

### 运行特定测试类

```bash
# 视角识别测试
docker exec it-doc-helper-backend pytest tests/test_regression/test_multi_view_processing.py::TestViewClassification -v

# 视角注册表测试
docker exec it-doc-helper-backend pytest tests/test_regression/test_multi_view_processing.py::TestViewRegistry -v

# 多视角容器测试
docker exec it-doc-helper-backend pytest tests/test_regression/test_multi_view_processing.py::TestMultiViewContainer -v
```

### 运行特定测试方法

```bash
docker exec it-doc-helper-backend pytest tests/test_regression/test_multi_view_processing.py::TestViewClassification::test_detect_qa_structure -v
```

## 测试覆盖的核心功能

### 1. 多视角独立性（难点1）

- ✅ 每个视角的处理结果独立存储
- ✅ 一个视角的失败不影响其他视角
- ✅ 每个视角使用独立的事务

### 2. 特征强度作为决策依据（难点2）

- ✅ 缓存key基于系统检测的特征得分
- ✅ 系统检测得分用于UI和算力分配决策
- ✅ 主视角用于UI初始状态，但不影响存储

### 3. 视角无关的中间结果（难点3）

- ✅ 中间结果不包含任何视角相关信息
- ✅ 所有视角共享同一份中间结果
- ✅ 切换视角时复用中间结果

### 4. 主次视角优先级（难点4）

- ✅ 主视角优先处理，快速返回
- ✅ 次视角可以异步处理
- ✅ UI层反映主次视角的处理状态

## 测试结果示例

```
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-7.4.3, pluggy-1.6.0
rootdir: /app
collected 25 items

tests/test_regression/test_multi_view_processing.py::TestViewClassification::test_detect_qa_structure PASSED
tests/test_regression/test_multi_view_processing.py::TestViewClassification::test_detect_component_relationships PASSED
tests/test_regression/test_multi_view_processing.py::TestViewClassification::test_detect_usage_flow PASSED
tests/test_regression/test_multi_view_processing.py::TestViewRegistry::test_view_registry_registration PASSED
tests/test_regression/test_multi_view_processing.py::TestViewRegistry::test_get_processor PASSED
tests/test_regression/test_multi_view_processing.py::TestMultiViewContainer::test_create_container PASSED
...

============================== 25 passed in 2.34s ==============================
```

## 注意事项

1. **数据库依赖**：部分测试需要数据库连接，确保测试数据库已配置
2. **异步测试**：使用`@pytest.mark.asyncio`标记异步测试
3. **测试隔离**：每个测试应该独立运行，不依赖其他测试的状态
4. **阈值调整**：检测得分的阈值可能需要根据实际数据调整

## 持续改进

- 添加更多边界情况测试
- 增加性能测试
- 添加并发处理测试
- 完善错误处理测试

---

**文档版本**：v1.0  
**创建时间**：2025-12-22

