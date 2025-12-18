# .doc 文件格式支持可行性分析

## 一、背景

当前系统支持的文件格式：
- PDF (`.pdf`)
- Word (`.docx`) - 使用 `python-docx` 库
- PPT (`.pptx`) - 使用 `python-pptx` 库
- Markdown (`.md`)
- TXT (`.txt`)

**需求**：扩展系统支持 `.doc` 格式（Microsoft Word 97-2003 二进制格式）

## 二、技术分析

### 2.1 格式差异

| 特性 | .docx | .doc |
|------|-------|------|
| 格式类型 | Office Open XML（ZIP 压缩的 XML） | 二进制格式（OLE2 Compound Document） |
| 标准 | 开放标准（ECMA-376, ISO/IEC 29500） | 专有格式（Microsoft 私有） |
| 解析难度 | 低（结构化 XML） | 高（需要解析二进制结构） |
| 库支持 | `python-docx` 原生支持 | 需要专门工具 |

### 2.2 技术方案对比

#### 方案 1：使用 `antiword`（推荐 ⭐⭐⭐⭐⭐）

**优点**：
- ✅ 轻量级（约 1MB），资源占用小
- ✅ 纯文本提取速度快
- ✅ 跨平台（Linux/Unix/MacOS）
- ✅ 无外部依赖（不需要安装 Word 或 LibreOffice）
- ✅ 适合 Docker 容器环境
- ✅ 开源免费

**缺点**：
- ❌ 只提取纯文本，丢失格式信息（表格、列表等）
- ❌ 不支持复杂对象（图片、嵌入对象）
- ❌ 对中文支持可能有限（需要测试）

**实现方式**：
```python
import subprocess
import os

def extract_doc_antiword(file_path: str) -> str:
    """使用 antiword 提取 .doc 文件内容"""
    try:
        result = subprocess.run(
            ['antiword', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout
        else:
            raise Exception(f"antiword 执行失败: {result.stderr}")
    except FileNotFoundError:
        raise Exception("antiword 未安装，请先安装: apt-get install antiword")
```

**Dockerfile 修改**：
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    antiword \
    && rm -rf /var/lib/apt/lists/*
```

**适用场景**：适合大多数场景，特别是只需要提取文本内容的场景

---

#### 方案 2：使用 `unoconv` + LibreOffice（备选 ⭐⭐⭐⭐）

**优点**：
- ✅ 功能强大，支持格式转换
- ✅ 可以转换为 `.docx` 后使用 `python-docx` 处理
- ✅ 保留更多格式信息（表格、列表等）
- ✅ 跨平台支持

**缺点**：
- ❌ 依赖重（LibreOffice 约 200MB+）
- ❌ 需要启动 LibreOffice 服务（资源消耗大）
- ❌ 处理速度较慢
- ❌ Docker 镜像体积显著增大

**实现方式**：
```python
import subprocess
import os
import tempfile

def extract_doc_unoconv(file_path: str) -> str:
    """使用 unoconv 将 .doc 转换为 .docx，然后提取"""
    try:
        # 转换为 .docx
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "output.docx")
            result = subprocess.run(
                ['unoconv', '-f', 'docx', '-o', docx_path, file_path],
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                raise Exception(f"unoconv 转换失败: {result.stderr}")
            
            # 使用 python-docx 提取
            from docx import Document
            doc = Document(docx_path)
            content_parts = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(content_parts)
    except FileNotFoundError:
        raise Exception("unoconv 未安装")
```

**Dockerfile 修改**：
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libreoffice \
    unoconv \
    && rm -rf /var/lib/apt/lists/*
```

**适用场景**：需要保留格式信息的场景（但会增加系统复杂度）

---

#### 方案 3：使用 `textract`（不推荐 ⭐⭐）

**优点**：
- ✅ 统一的 API 接口
- ✅ 支持多种格式

**缺点**：
- ❌ 依赖系统工具（需要安装多个后端）
- ❌ 配置复杂
- ❌ 维护成本高
- ❌ 性能不稳定

---

#### 方案 4：使用 `win32com.client`（不适用 ⭐）

**优点**：
- ✅ 功能完整，支持所有 Word 特性

**缺点**：
- ❌ 仅 Windows 系统
- ❌ 需要安装 Microsoft Word
- ❌ 不适合 Docker 容器环境
- ❌ 无法在 Linux 服务器上运行

---

## 三、推荐方案

### 3.1 首选方案：`antiword`

**理由**：
1. **轻量级**：适合容器化部署，不会显著增加镜像大小
2. **性能好**：纯文本提取速度快，资源占用小
3. **稳定性高**：成熟工具，维护成本低
4. **满足需求**：对于 IT 文档处理，文本内容是最重要的

**限制说明**：
- 只提取纯文本，不保留格式（表格、列表等会转换为文本）
- 对于复杂格式的文档，可能需要用户手动转换为 `.docx`

### 3.2 实现步骤

1. **后端修改**：
   - 在 `DocumentExtractor` 中添加 `extract_doc` 方法
   - 更新 `extract` 方法支持 `doc` 类型
   - 在 `requirements.txt` 中无需添加 Python 包（使用系统工具）

2. **Dockerfile 修改**：
   - 安装 `antiword` 工具

3. **配置修改**：
   - 在 `config.py` 的 `ALLOWED_EXTENSIONS` 中添加 `doc`
   - 更新前端 `FileUpload` 组件允许 `.doc` 文件

4. **测试**：
   - 单元测试：测试各种 `.doc` 文件提取
   - 集成测试：完整流程测试
   - 中文支持测试：确保中文文档能正确提取

## 四、风险评估

### 4.1 技术风险

| 风险项 | 风险等级 | 影响 | 应对措施 |
|--------|---------|------|---------|
| 中文编码问题 | 中 | 中文文档提取乱码 | 测试并配置正确的编码参数 |
| 复杂格式丢失 | 中 | 表格、列表格式丢失 | 文档说明，建议用户使用 `.docx` |
| 文件损坏无法提取 | 低 | 处理失败 | 异常处理，返回友好错误信息 |
| 性能问题 | 低 | 大文件处理慢 | 已有文档大小限制（30MB） |

### 4.2 兼容性风险

- **文件版本**：`.doc` 格式有多个版本（Word 97/2000/2003），`antiword` 支持主流版本
- **特殊内容**：宏、嵌入对象等无法提取（但通常 IT 文档不包含这些）

### 4.3 维护成本

- **低**：`antiword` 是成熟工具，维护成本低
- **依赖管理**：系统级依赖，需要 Dockerfile 中管理

## 五、实施建议

### 5.1 分阶段实施

**阶段 1：基础支持（推荐）**
- 使用 `antiword` 实现基础文本提取
- 支持纯文本 `.doc` 文件
- 文档说明格式限制

**阶段 2：增强支持（可选）**
- 如果用户反馈需要保留格式，再考虑 `unoconv` + LibreOffice 方案
- 评估性能影响和资源消耗

### 5.2 用户体验优化

1. **上传提示**：
   - 支持 `.doc` 格式，但建议使用 `.docx` 以获得更好的格式支持
   
2. **错误处理**：
   - 如果提取失败，提示用户转换为 `.docx` 格式重试

3. **文档说明**：
   - 在帮助文档中说明 `.doc` 格式的限制（只提取文本，不保留格式）

## 六、成本评估

### 6.1 开发成本

- **开发时间**：2-4 小时
  - 后端实现：1-2 小时
  - Dockerfile 修改：0.5 小时
  - 配置和前端修改：0.5 小时
  - 测试：1 小时

### 6.2 运维成本

- **镜像大小**：增加约 1-2MB（`antiword`）
- **运行时资源**：几乎无影响（轻量级工具）
- **维护成本**：低（系统工具，稳定）

### 6.3 如果使用 LibreOffice 方案

- **镜像大小**：增加约 200-300MB
- **运行时资源**：内存增加约 100-200MB
- **处理速度**：较慢（需要启动 LibreOffice 服务）

## 七、结论

### 7.1 可行性评估

✅ **高度可行**

- 技术方案成熟可靠
- 实现难度低
- 成本可控
- 风险可接受

### 7.2 推荐决策

**建议采用方案 1（antiword）**，理由：
1. 满足大多数用户需求（文本提取）
2. 系统影响最小（轻量级）
3. 实施成本低
4. 维护简单

**如果后续需要格式保留功能，再考虑方案 2（unoconv）**

### 7.3 实施优先级

- **优先级**：中高
- **建议时机**：在下一个迭代周期实施
- **依赖关系**：无特殊依赖，可独立实施

---

## 附录：相关资源

- [antiword 官网](http://www.winfield.demon.nl/)
- [antiword GitHub](https://github.com/rsdoiel/antiword)
- [unoconv 文档](https://github.com/unoconv/unoconv)
- [LibreOffice 文档](https://www.libreoffice.org/)

