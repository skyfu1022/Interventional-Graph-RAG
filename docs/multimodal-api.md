# 多模态查询 API 使用指南

## 概述

多模态查询 API 支持结合文本和图像/表格数据的知识图谱查询。该功能基于 FastAPI 的文件上传功能，使用 `multipart/form-data` 格式处理文件。

## 端点信息

- **URL**: `POST /api/v1/query/multimodal`
- **认证**: 需要 API Key（如果配置了 `API_KEYS` 环境变量）
- **速率限制**: 遵循全局速率限制配置

## 请求参数

### 表单字段（Form Fields）

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `query` | string | 是 | - | 查询文本 |
| `image` | file | 否 | - | 图像文件（支持 jpg, jpeg, png, gif） |
| `table_data` | file | 否 | - | 表格文件（支持 csv, xlsx, xls） |
| `mode` | string | 否 | `hybrid` | 查询模式：`naive`, `local`, `global`, `hybrid`, `mix`, `bypass` |
| `graph_id` | string | 否 | - | 图谱 ID（可选） |

### 文件限制

- **最大文件大小**: 10MB
- **支持的图像格式**: .jpg, .jpeg, .png, .gif
- **支持的表格格式**: .csv, .xlsx, .xls

## 响应格式

```json
{
  "query": "查询文本",
  "answer": "答案内容",
  "mode": "hybrid",
  "graph_id": "graph-123",
  "sources": [
    {
      "chunk_id": "chunk-001",
      "content": "相关内容片段",
      "score": 0.95,
      "metadata": {}
    }
  ],
  "context": {
    "multimodal_notice": "SDK 暂未实现完整的多模态查询功能..."
  },
  "graph_context": {
    "entities": [],
    "relationships": []
  },
  "retrieval_count": 5,
  "latency_ms": 150
}
```

## 使用示例

### 1. 图像查询

查询医学图像（如 X 光片、CT 片等）：

```bash
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -H "X-API-Key: your-api-key" \
  -F "query=这张X光片显示什么异常？" \
  -F "image=@/path/to/xray.jpg" \
  -F "mode=hybrid"
```

### 2. 表格数据查询

分析医学表格数据（如血常规、实验室检查结果等）：

```bash
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -H "X-API-Key: your-api-key" \
  -F "query=分析这个血常规检查结果，有哪些异常？" \
  -F "table_data=@/path/to/blood_test.csv" \
  -F "mode=hybrid"
```

### 3. 图像 + 表格查询

结合图像和表格数据进行综合分析：

```bash
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -H "X-API-Key: your-api-key" \
  -F "query=结合影像学和实验室检查结果，给出诊断建议" \
  -F "image=@/path/to/ct_scan.jpg" \
  -F "table_data=@/path/to/lab_results.xlsx" \
  -F "mode=hybrid"
```

### 4. 仅文本查询（无文件）

如果未上传文件，端点会自动降级为普通查询：

```bash
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -H "X-API-Key: your-api-key" \
  -F "query=什么是糖尿病？" \
  -F "mode=hybrid"
```

## Python 客户端示例

使用 Python 的 `requests` 库调用多模态查询 API：

```python
import requests

API_URL = "http://localhost:8000/api/v1/query/multimodal"
API_KEY = "your-api-key"  # 如果需要认证

def multimodal_query(
    query: str,
    image_path: str | None = None,
    table_path: str | None = None,
    mode: str = "hybrid",
    graph_id: str | None = None,
) -> dict:
    """执行多模态查询。

    Args:
        query: 查询文本
        image_path: 图像文件路径（可选）
        table_path: 表格文件路径（可选）
        mode: 查询模式
        graph_id: 图谱 ID（可选）

    Returns:
        查询结果字典
    """
    # 准备表单数据
    data = {
        "query": query,
        "mode": mode,
    }

    if graph_id:
        data["graph_id"] = graph_id

    # 准备文件
    files = {}
    if image_path:
        files["image"] = open(image_path, "rb")

    if table_path:
        files["table_data"] = open(table_path, "rb")

    # 准备请求头
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    try:
        # 发送请求
        response = requests.post(API_URL, data=data, files=files, headers=headers)
        response.raise_for_status()

        return response.json()

    finally:
        # 关闭文件
        for f in files.values():
            f.close()


# 使用示例
if __name__ == "__main__":
    # 图像查询
    result = multimodal_query(
        query="这张X光片显示什么？",
        image_path="xray.jpg",
        mode="hybrid",
    )
    print("答案:", result["answer"])

    # 表格查询
    result = multimodal_query(
        query="分析血常规检查结果",
        table_path="blood_test.csv",
        mode="hybrid",
    )
    print("答案:", result["answer"])
```

## 错误处理

### 常见错误

#### 1. 文件类型不支持

```json
{
  "detail": {
    "error": "ValidationError",
    "message": "不支持的文件类型: .bmp",
    "allowed_types": [".jpg", ".jpeg", ".png", ".gif"]
  }
}
```

**解决方案**: 确保上传的文件是支持的格式。

#### 2. 文件过大

```json
{
  "detail": {
    "error": "FileTooLarge",
    "message": "文件大小超过限制: 10MB",
    "file_size": 15728640,
    "max_size": 10485760
  }
}
```

**解决方案**: 压缩或分割文件，确保文件大小在 10MB 以内。

#### 3. 查询文本为空

```json
{
  "detail": {
    "error": "ValidationError",
    "message": "查询文本不能为空"
  }
}
```

**解决方案**: 确保提供有效的查询文本。

## 实现细节

### 文件处理流程

1. **文件验证**: 检查文件名、扩展名和大小
2. **保存临时文件**: 将上传文件保存到临时目录
3. **文件处理**:
   - 图像：编码为 Base64（供 SDK 使用）
   - 表格：解析为 JSON 格式（待实现）
4. **调用 SDK**: 传递文件路径或编码后的数据
5. **清理临时文件**: 查询完成后删除临时文件

### SDK 集成

- 如果 SDK 实现了 `multimodal_query()` 方法，将直接调用
- 否则，使用增强的文本查询，并在响应中添加提示信息

### 查询模式

支持以下查询模式：

- `naive`: 简单向量检索
- `local`: 局部图谱检索
- `global`: 全局图谱检索
- `hybrid`: 混合检索（默认）
- `mix`: 混合向量 + 图谱检索
- `bypass`: 绕过检索，直接生成答案

## 性能考虑

1. **文件大小**: 10MB 的限制是为了平衡性能和实用性
2. **临时文件**: 使用 `tempfile` 模块确保安全清理
3. **异步处理**: 文件读取和 SDK 调用都是异步的
4. **错误恢复**: 即使查询失败，也会清理临时文件

## 未来改进

- [ ] 实现表格数据解析（使用 pandas）
- [ ] 支持更多图像格式（DICOM 医学影像）
- [ ] 实现真正的多模态查询（SDK 层）
- [ ] 支持批量文件上传
- [ ] 添加文件预处理（压缩、格式转换）

## 相关文件

- 路由实现: `/src/api/routes/multimodal.py`
- Schema 定义: `/src/api/schemas/multimodal.py`
- 依赖注入: `/src/api/deps.py`
- 应用配置: `/src/api/app.py`
