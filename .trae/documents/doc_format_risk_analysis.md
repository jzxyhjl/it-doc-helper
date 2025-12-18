# .doc 格式支持 - 稳定性风险分析

## 一、风险识别

### 1.1 引入外部系统工具的风险

引入 `antiword`（通过 `subprocess` 调用）会带来以下风险：

| 风险类别 | 具体风险 | 影响程度 | 发生概率 |
|---------|---------|---------|---------|
| **依赖风险** | antiword 未安装或版本不兼容 | 高 | 低（Docker 环境可控） |
| **进程管理** | subprocess 调用卡死、超时 | 中 | 中（大文件或损坏文件） |
| **编码问题** | 中文文档提取乱码 | 中 | 中（需要测试验证） |
| **资源消耗** | 进程开销、内存占用 | 低 | 低（antiword 轻量） |
| **错误传播** | 异常处理不当影响主流程 | 高 | 低（已有异常处理机制） |
| **兼容性** | 某些 .doc 版本不支持 | 中 | 中（旧版本 Word 文件） |

### 1.2 与现有系统的对比

| 特性 | 现有格式（.docx/.pdf） | 新增格式（.doc） |
|------|----------------------|-----------------|
| **依赖类型** | Python 库（纯 Python） | 系统工具（C 程序） |
| **错误处理** | Python 异常（可控） | 进程退出码（需转换） |
| **超时控制** | asyncio 原生支持 | 需要手动实现 |
| **资源隔离** | 同进程内 | 独立进程 |
| **调试难度** | 低（Python 堆栈） | 中（需查看进程日志） |

## 二、具体风险场景分析

### 2.1 场景 1：antiword 未安装或不可用

**风险描述**：
- Docker 镜像构建时遗漏安装
- 系统更新导致工具丢失
- 权限问题导致无法执行

**影响**：
- `.doc` 文件处理完全失败
- 用户收到不友好的错误信息

**缓解措施**：
```python
# 1. 启动时检查工具可用性
def check_antiword_available() -> bool:
    try:
        result = subprocess.run(
            ['antiword', '-v'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

# 2. 优雅降级
if not check_antiword_available():
    logger.warning("antiword 不可用，.doc 格式支持已禁用")
    # 在配置中标记 .doc 为不支持
```

### 2.2 场景 2：subprocess 调用超时或卡死

**风险描述**：
- 大文件处理时间过长
- 损坏文件导致进程挂起
- 系统资源不足导致进程阻塞

**影响**：
- 任务长时间无响应
- Celery worker 被阻塞
- 影响其他任务处理

**缓解措施**：
```python
# 1. 强制超时控制
async def extract_doc_with_timeout(file_path: str, timeout: int = 30) -> str:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_extract_doc_sync, file_path),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        raise ProcessingException(
            status=ProcessingStatus.TIMEOUT,
            error_type=ErrorType.TIMEOUT,
            error_message=f".doc 文件提取超时（>{timeout}秒），文件可能过大或损坏",
            user_actions=[
                {"action": "retry", "label": "重试"},
                {"action": "convert_to_docx", "label": "转换为 .docx 格式"}
            ]
        )

# 2. 文件大小预检查
if os.path.getsize(file_path) > 20 * 1024 * 1024:  # 20MB
    logger.warning("文件较大，.doc 提取可能较慢", file_path=file_path)
```

### 2.3 场景 3：编码问题导致中文乱码

**风险描述**：
- antiword 默认输出可能不是 UTF-8
- 中文文档提取后乱码
- 影响后续 AI 处理质量

**影响**：
- 提取内容无法使用
- AI 处理结果不准确
- 用户体验差

**缓解措施**：
```python
# 1. 显式指定编码
result = subprocess.run(
    ['antiword', '-m', 'UTF-8.txt', file_path],  # -m 参数指定映射文件
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'  # 遇到编码错误时替换而非失败
)

# 2. 编码检测和修复
if result.returncode == 0:
    content = result.stdout
    # 检测并修复常见编码问题
    if not _is_valid_utf8(content):
        content = _fix_encoding(content)
    return content
```

### 2.4 场景 4：损坏或特殊格式的 .doc 文件

**风险描述**：
- 文件损坏导致 antiword 崩溃
- 特殊版本 .doc 格式不支持
- 包含宏或嵌入对象的文件

**影响**：
- 提取失败
- 进程异常退出
- 需要用户手动处理

**缓解措施**：
```python
# 1. 完善的错误处理
try:
    result = subprocess.run(
        ['antiword', file_path],
        capture_output=True,
        timeout=30,
        check=False  # 不自动抛出异常
    )
    
    if result.returncode != 0:
        # 分析错误类型
        error_msg = result.stderr.decode('utf-8', errors='ignore')
        if 'corrupt' in error_msg.lower():
            raise ProcessingException(
                status=ProcessingStatus.FAILED,
                error_type=ErrorType.FILE_CORRUPTED,
                error_message="文件可能损坏，无法提取内容",
                user_actions=[
                    {"action": "re_upload", "label": "重新上传"},
                    {"action": "convert_to_docx", "label": "转换为 .docx 格式"}
                ]
            )
        else:
            raise ProcessingException(...)
    
    # 2. 验证提取结果
    content = result.stdout.decode('utf-8', errors='replace')
    if len(content.strip()) < 10:  # 内容过少，可能提取失败
        raise ProcessingException(
            status=ProcessingStatus.LOW_QUALITY,
            error_type=ErrorType.PARSE_ERROR,
            error_message="提取内容过少，文件可能无法正确解析",
            user_actions=[...]
        )
```

### 2.5 场景 5：影响现有格式处理

**风险描述**：
- 代码修改引入 bug
- 异常处理不当影响其他格式
- 配置错误导致所有格式失败

**影响**：
- 系统整体稳定性下降
- 现有功能受影响

**缓解措施**：
```python
# 1. 完全隔离的实现
# .doc 提取独立方法，不影响现有代码
@staticmethod
async def extract_doc(file_path: str) -> str:
    """独立的 .doc 提取方法，不影响其他格式"""
    # ... 实现

# 2. 在 extract() 方法中安全集成
extractors = {
    'pdf': DocumentExtractor.extract_pdf,
    'docx': DocumentExtractor.extract_word,
    'doc': DocumentExtractor.extract_doc,  # 新增，独立实现
    # ...
}

# 3. 异常隔离
try:
    return await extractor(file_path)
except ProcessingException:
    # .doc 特定异常，不影响其他格式
    raise
except Exception as e:
    # 其他异常按原逻辑处理
    logger.error(f"{file_type}提取失败", error=str(e))
    raise
```

## 三、风险缓解策略

### 3.1 技术层面

#### 策略 1：渐进式实施 + 功能开关

```python
# config.py
class Settings(BaseSettings):
    # 功能开关
    ENABLE_DOC_SUPPORT: bool = False  # 默认关闭，测试稳定后开启
    
    def is_doc_supported(self) -> bool:
        """检查 .doc 格式是否支持"""
        if not self.ENABLE_DOC_SUPPORT:
            return False
        # 运行时检查工具可用性
        return check_antiword_available()
```

**优势**：
- 可以随时关闭功能
- 不影响现有系统
- 便于灰度发布

#### 策略 2：完善的异常处理和降级

```python
@staticmethod
async def extract_doc(file_path: str) -> str:
    """提取 .doc 文件，带完善的错误处理"""
    try:
        # 1. 预检查
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 2. 检查工具可用性
        if not check_antiword_available():
            raise ProcessingException(
                status=ProcessingStatus.FAILED,
                error_type=ErrorType.UNSUPPORTED_FORMAT,
                error_message=".doc 格式支持暂时不可用（工具未安装）",
                user_actions=[
                    {"action": "convert_to_docx", "label": "请转换为 .docx 格式"}
                ]
            )
        
        # 3. 带超时的提取
        content = await extract_doc_with_timeout(file_path, timeout=30)
        
        # 4. 结果验证
        if len(content.strip()) < 10:
            raise ProcessingException(
                status=ProcessingStatus.LOW_QUALITY,
                error_type=ErrorType.PARSE_ERROR,
                error_message="提取内容过少，可能无法正确解析",
                user_actions=[...]
            )
        
        return content
        
    except ProcessingException:
        # 已知异常，直接抛出
        raise
    except subprocess.TimeoutExpired:
        # 超时异常
        raise ProcessingException(...)
    except Exception as e:
        # 未知异常，包装为 ProcessingException
        logger.error(".doc 提取失败", file_path=file_path, error=str(e))
        raise ProcessingException(
            status=ProcessingStatus.FAILED,
            error_type=ErrorType.PARSE_ERROR,
            error_message=f".doc 文件提取失败: {str(e)[:100]}",
            error_details={"error_type": type(e).__name__},
            user_actions=[
                {"action": "retry", "label": "重试"},
                {"action": "convert_to_docx", "label": "转换为 .docx 格式"}
            ]
        )
```

#### 策略 3：监控和告警

```python
# 添加指标监控
@staticmethod
async def extract_doc(file_path: str) -> str:
    start_time = time.time()
    try:
        content = await _extract_doc_internal(file_path)
        
        # 记录成功指标
        duration = time.time() - start_time
        logger.info(
            ".doc 提取成功",
            file_path=file_path,
            duration=duration,
            content_length=len(content)
        )
        
        return content
    except Exception as e:
        # 记录失败指标
        logger.error(
            ".doc 提取失败",
            file_path=file_path,
            error=str(e),
            duration=time.time() - start_time
        )
        raise
```

### 3.2 运维层面

#### 策略 1：Docker 镜像验证

```dockerfile
# Dockerfile
RUN apt-get update && apt-get install -y \
    antiword \
    && rm -rf /var/lib/apt/lists/*

# 验证安装
RUN antiword -v || (echo "antiword 安装失败" && exit 1)
```

#### 策略 2：健康检查

```python
# 在应用启动时检查
async def startup_check():
    """启动时检查依赖"""
    if not check_antiword_available():
        logger.warning("antiword 不可用，.doc 格式支持已禁用")
        # 从允许的扩展名中移除 doc（如果配置了）
    else:
        logger.info("antiword 可用，.doc 格式支持已启用")
```

### 3.3 用户体验层面

#### 策略 1：清晰的错误提示

```python
# 用户友好的错误信息
user_actions = [
    {
        "action": "convert_to_docx",
        "label": "转换为 .docx 格式",
        "description": "使用 Microsoft Word 或 LibreOffice 将文件另存为 .docx 格式，以获得更好的支持"
    },
    {
        "action": "retry",
        "label": "重试处理",
        "description": "如果问题持续，请尝试转换为 .docx 格式"
    }
]
```

#### 策略 2：上传时提示

```typescript
// 前端提示
if (fileExtension === 'doc') {
  showWarning(
    '.doc 格式支持有限，建议使用 .docx 格式以获得更好的处理效果'
  )
}
```

## 四、风险评估矩阵

| 风险项 | 发生概率 | 影响程度 | 风险等级 | 缓解措施有效性 | 剩余风险 |
|--------|---------|---------|---------|--------------|---------|
| antiword 未安装 | 低 | 高 | 中 | 高（Docker 可控） | 低 |
| 进程超时/卡死 | 中 | 中 | 中 | 高（超时控制） | 低 |
| 中文编码问题 | 中 | 中 | 中 | 中（需测试） | 中 |
| 损坏文件处理 | 中 | 低 | 低 | 高（异常处理） | 低 |
| 影响现有功能 | 低 | 高 | 中 | 高（代码隔离） | 低 |

**总体风险等级**：**中低**

## 五、推荐实施策略

### 5.1 保守策略（推荐）

**阶段 1：基础实现 + 功能开关**
- 实现 `.doc` 提取功能
- 添加功能开关（默认关闭）
- 完善异常处理和降级
- 单元测试和集成测试

**阶段 2：内部测试**
- 开启功能开关，内部测试
- 收集错误日志和性能数据
- 修复发现的问题

**阶段 3：灰度发布**
- 小范围用户开启
- 监控错误率和性能
- 根据反馈调整

**阶段 4：全量发布**
- 稳定后全量开启
- 持续监控

### 5.2 技术实施要点

1. **代码隔离**：`.doc` 提取完全独立，不影响现有代码
2. **异常隔离**：使用 `ProcessingException`，不影响其他格式
3. **超时控制**：强制超时，防止卡死
4. **降级策略**：工具不可用时优雅降级
5. **监控告警**：记录所有操作，便于问题排查

### 5.3 回滚方案

如果出现问题，可以：
1. **快速回滚**：关闭功能开关，立即禁用 `.doc` 支持
2. **代码回滚**：Git 回滚到上一版本
3. **Docker 回滚**：使用上一版本的镜像

## 六、结论

### 6.1 风险可控性

✅ **风险可控**，理由：
1. 已有完善的异常处理机制（`ProcessingException`）
2. 可以完全隔离实现，不影响现有功能
3. 有功能开关，可以随时禁用
4. 轻量级工具，资源消耗小

### 6.2 建议

**建议采用保守策略实施**：
1. 先实现基础功能，添加功能开关
2. 充分测试后再开启
3. 持续监控，及时发现问题
4. 准备回滚方案

**不建议**：
- 直接全量开启（风险较高）
- 忽略异常处理（可能导致系统不稳定）
- 不进行充分测试（可能影响用户体验）

### 6.3 替代方案

如果风险仍然不可接受，可以考虑：
1. **用户自行转换**：提示用户转换为 `.docx` 格式
2. **使用云服务**：调用第三方 API 进行转换（增加成本）
3. **延迟实施**：等系统更稳定后再考虑

---

## 附录：实施检查清单

- [ ] 实现 `.doc` 提取功能
- [ ] 添加功能开关
- [ ] 完善异常处理
- [ ] 添加超时控制
- [ ] 实现降级策略
- [ ] 添加监控日志
- [ ] 单元测试
- [ ] 集成测试
- [ ] 中文编码测试
- [ ] 损坏文件测试
- [ ] 大文件测试
- [ ] 性能测试
- [ ] Docker 镜像验证
- [ ] 文档更新
- [ ] 回滚方案准备

