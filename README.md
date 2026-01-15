# LLM Stream Parser

[![Tests](https://github.com/yourusername/llm-stream-parser/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/llm-stream-parser/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/llm-stream-parser)](https://pypi.org/project/llm-stream-parser/)
[![Python](https://img.shields.io/pypi/pyversions/llm-stream-parser)](https://pypi.org/project/llm-stream-parser/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个用于实时解析大语言模型（LLM）流式响应的 Python 库，支持基于标签的内容提取。

## ✨ 特性

- 🚀 **实时解析**：在流式接收过程中实时解析内容，无需等待完整响应
- 🏷️ **标签提取**：支持 XML 风格标签的内容提取（如 `<think>...</think>`）
- 📊 **结构化输出**：将流式内容转换为结构化的消息对象
- ⚡ **流式模式**：支持标签内内容的实时流式解析
- 🔧 **灵活配置**：自定义标签映射和解析行为
- 🧪 **完整测试**：全面的单元测试和异步测试覆盖
- 📦 **零依赖**：仅依赖 Pydantic，轻量级设计

## 📦 安装

```bash
pip install llm-stream-parser
```

## 🚀 快速开始

### 基础用法

```python
from llm_stream_parser import StreamParser

# 创建解析器，定义标签映射
parser = StreamParser(tags={"think": "思考", "tool": "工具调用"})

# 模拟流式接收的 chunks
chunks = [
    "</think>我需要帮",
    "助用户查",
    "询天气",
    "我需要帮",
    "您查询天",
    "气信息。<tool>调用天气API</tool>",
    "这就是全部结果。"
]

# 逐个解析 chunk
for chunk in chunks:
    messages = parser.parse_chunk(chunk)
    for msg in messages:
        print(f"步骤{msg.step}: {msg.step_name} - {msg.content}")

# 处理剩余内容
final = parser.finalize()
if final:
    print(f"步骤{final.step}: {final.step_name} - {final.content}")
```

### 异步流处理

```python
import asyncio
from llm_stream_parser import process_llm_stream

async def mock_llm_stream():
    """模拟 LLM 流式响应"""
    yield "</think>思考内容"
    yield "回答内容"

async def main():
    tags = {"think": "思考"}
    async for msg in process_llm_stream(mock_llm_stream(), tags):
        print(f"步骤{msg.step}: {msg.step_name} - {msg.content}")

asyncio.run(main())
```

### 流式输出模式

```python
# 启用标签内流式输出
parser = StreamParser(
    tags={"think": "思考"},
    enable_tags_streaming=True  # 实时输出标签内内容
)

chunks = ["</think>思考", "内容", "继续", "</think>"]
for chunk in chunks:
    messages = parser.parse_chunk(chunk)
    for msg in messages:
        print(f"{msg.step_name}: {msg.content} (完整: {msg.is_complete})")
```

## 📖 API 文档

### StreamParser

核心解析器类。

#### 初始化参数

| 参数                    | 类型                     | 默认值  | 说明                           |
| ----------------------- | ------------------------ | ------- | ------------------------------ |
| `tags`                  | `Dict[str, str] \| None` | `None`  | 标签字典，映射标签名到步骤名称 |
| `enable_tags_streaming` | `bool`                   | `False` | 是否启用标签内流式输出         |

#### 方法

##### `parse_chunk(chunk: str) -> List[StreamMessage]`

解析一个新的文本块。

**参数：**

- `chunk`: 要解析的文本块

**返回：**

- 解析出的 `StreamMessage` 列表

##### `finalize() -> Optional[StreamMessage]`

当流结束时调用，处理缓冲区中剩余的内容。

**返回：**

- 最后的 `StreamMessage`，如果没有内容则返回 `None`

### StreamMessage

解析后的消息对象。

| 属性          | 类型   | 说明                                              |
| ------------- | ------ | ------------------------------------------------- |
| `step`        | `int`  | 步骤序号（按 step_name 分组计数）                 |
| `step_name`   | `str`  | 步骤名称                                          |
| `title`       | `str`  | 标题（可选）                                      |
| `content`     | `Any`  | 内容                                              |
| `is_complete` | `bool` | 标签是否闭合（True 表示闭合，False 表示流式输出） |

### process_llm_stream

异步流处理包装函数。

```python
async def process_llm_stream(
    stream: AsyncGenerator[str, None],
    tags: Optional[Dict[str, str]] = None,
    enable_tags_streaming: bool = False
) -> AsyncGenerator[StreamMessage, None]
```

**参数：**

- `stream`: 原始的文本流
- `tags`: 自定义标签字典
- `enable_tags_streaming`: 是否启用标签内流式输出

**返回：**

- 异步生成器，产出 `StreamMessage` 对象

## 🎯 使用场景

### 1. 展示模型思考过程

```python
parser = StreamParser(tags={"think": "思考中"})

# LLM 输出: "</think>让我分析一下这个问题...首先，我需要...</think>这是我的回答。"
# 解析后可以分别展示"思考中"和"回答"两个部分
```

### 2. 工具调用解析

```python
parser = StreamParser(tags={
    "tool": "工具调用",
    "result": "执行结果"
})

# LLM 输出: "我需要查询天气。<tool>get_weather(city='北京')</tool><result>晴天，25°C</result>"
# 解析后可以分别处理工具调用和结果
```

### 3. 多步骤任务分解

```python
parser = StreamParser(tags={
    "analysis": "分析",
    "planning": "规划",
    "execution": "执行",
    "summary": "总结"
})

# LLM 输出包含多个标签，解析后可以按步骤展示
```

## 🧪 测试

```bash
# 克隆仓库
git clone https://github.com/yourusername/llm-stream-parser.git
cd llm-stream-parser

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 查看覆盖率
pytest --cov=llm_stream_parser --cov-report=html
```

## 📝 标签格式规则

### 标签命名规则

- 必须以字母开头
- 只能包含字母、数字、下划线和连字符
- 示例：`think`, `tool_call`, `tool-call`, `ToolCall`

### 标签使用示例

```xml

<tool>工具调用</tool>
<analysis>分析内容</analysis>
<calculation>计算过程</calculation>
```

### 跨 Chunk 处理

解析器会自动处理标签和内容被分割到多个 chunk 的情况：

```python
# 以下 chunks 会被正确解析
chunks = [
    "<th", "ink>思考", "内容</", "think>"
]
```

## 🔧 高级用法

### 自定义步骤名称

```python
parser = StreamParser(tags={
    "think": "深度思考",
    "tool": "执行工具",
    "result": "返回结果"
})
```

### 处理未闭合标签

```python
parser = StreamParser(tags={"think": "思考"})

# 即使标签未闭合，finalize() 也会处理剩余内容
chunks = ["</think>思考内容"]
parser.parse_chunk(chunks[0])
final = parser.finalize()  # 会输出"思考内容"
```

### 无标签模式

```python
# 不配置标签，所有内容都作为"回答"处理
parser = StreamParser(tags=None)
```

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🔗 相关链接

- [GitHub 仓库](https://github.com/yourusername/llm-stream-parser)
- [PyPI 页面](https://pypi.org/project/llm-stream-parser/)
- [问题反馈](https://github.com/yourusername/llm-stream-parser/issues)

## 🙏 致谢

感谢所有贡献者和使用者！

---

**注意**：这是一个独立的开源项目，与任何特定的 LLM 提供商无关。它可以与任何支持流式输出的 LLM API 一起使用。
