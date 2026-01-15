# API 文档

本文档详细介绍了 `llm-stream-parser` 的 API 接口。

## 目录

- [StreamParser](#streamparser)
- [StreamMessage](#streammessage)
- [process_llm_stream](#process_llm_stream)

---

## StreamParser

核心解析器类，用于实时解析流式 LLM 响应。

### 构造函数

```python
StreamParser(tags: Optional[Dict[str, str]] = None, enable_tags_streaming: bool = False)
```

#### 参数

| 参数                    | 类型                     | 默认值  | 说明                                                                                                    |
| ----------------------- | ------------------------ | ------- | ------------------------------------------------------------------------------------------------------- |
| `tags`                  | `Dict[str, str] \| None` | `None`  | 标签字典，映射标签名到步骤名称。例如：`{"think": "思考", "tool": "工具调用"}`                           |
| `enable_tags_streaming` | `bool`                   | `False` | 是否启用标签内流式输出。`False` 表示等待标签结束后才输出完整内容，`True` 表示实时输出流式内容和最终输出 |

#### 示例

```python
from llm_stream_parser import StreamParser

# 基础用法
parser = StreamParser(tags={"think": "思考", "tool": "工具调用"})

# 启用流式输出
parser = StreamParser(
    tags={"think": "思考"},
    enable_tags_streaming=True
)

# 无标签模式
parser = StreamParser(tags=None)
```

### 方法

#### parse_chunk

解析一个新的文本块。

```python
def parse_chunk(self, chunk: str) -> List[StreamMessage]
```

**参数：**

- `chunk` (`str`): 要解析的文本块

**返回：**

- `List[StreamMessage]`: 解析出的消息列表

**示例：**

```python
parser = StreamParser(tags={"think": "思考"})

messages = parser.parse_chunk("</think>思考内容")
for msg in messages:
    print(f"{msg.step_name}: {msg.content}")
```

#### finalize

当流结束时调用，处理缓冲区中剩余的内容。

```python
def finalize(self) -> Optional[StreamMessage]
```

**返回：**

- `Optional[StreamMessage]`: 最后的消息，如果没有内容则返回 `None`

**示例：**

```python
parser = StreamParser(tags={"think": "思考"})

# 解析所有 chunks
for chunk in chunks:
    parser.parse_chunk(chunk)

# 处理剩余内容
final = parser.finalize()
if final:
    print(f"最终内容: {final.content}")
```

---

## StreamMessage

解析后的消息对象，表示从流式响应中提取的结构化内容。

### 属性

| 属性          | 类型   | 说明                                                  |
| ------------- | ------ | ----------------------------------------------------- |
| `step`        | `int`  | 步骤序号（按 `step_name` 分组计数）                   |
| `step_name`   | `str`  | 步骤名称                                              |
| `title`       | `str`  | 标题（可选，默认为空字符串）                          |
| `content`     | `Any`  | 内容                                                  |
| `is_complete` | `bool` | 标签是否闭合（`True` 表示闭合，`False` 表示流式输出） |

### 示例

```python
from llm_stream_parser import StreamMessage

# 创建消息
msg = StreamMessage(
    step=1,
    step_name="思考",
    title="",
    content="这是思考内容",
    is_complete=True
)

print(f"步骤{msg.step}: {msg.step_name}")
print(f"内容: {msg.content}")
print(f"完整: {msg.is_complete}")
```

### JSON 序列化

`StreamMessage` 继承自 Pydantic 的 `BaseModel`，支持 JSON 序列化：

```python
import json

msg = StreamMessage(
    step=1,
    step_name="思考",
    content="思考内容",
    is_complete=True
)

# 转换为 JSON
json_str = msg.model_dump_json()
print(json_str)

# 从 JSON 解析
msg2 = StreamMessage.model_validate_json(json_str)
```

---

## process_llm_stream

异步流处理包装函数，用于处理异步的 LLM 流式响应。

### 函数签名

```python
async def process_llm_stream(
    stream: AsyncGenerator[str, None],
    tags: Optional[Dict[str, str]] = None,
    enable_tags_streaming: bool = False
) -> AsyncGenerator[StreamMessage, None]
```

### 参数

| 参数                    | 类型                        | 默认值       | 说明                             |
| ----------------------- | --------------------------- | ------------ | -------------------------------- |
| `stream`                | `AsyncGenerator[str, None]` | 原始的文本流 |
| `tags`                  | `Dict[str, str] \| None`    | `None`       | 自定义标签字典，用于解析特定标签 |
| `enable_tags_streaming` | `bool`                      | `False`      | 是否启用标签内流式输出           |

### 返回

- `AsyncGenerator[StreamMessage, None]`: 异步生成器，产出解析后的消息对象

### 示例

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

### 与真实 LLM API 集成

```python
import asyncio
from openai import AsyncOpenAI
from llm_stream_parser import process_llm_stream

async def main():
    client = AsyncOpenAI()

    async def llm_stream():
        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "分析这个问题"}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    tags = {"think": "思考"}
    async for msg in process_llm_stream(llm_stream(), tags):
        print(f"{msg.step_name}: {msg.content}")

asyncio.run(main())
```

---

## 标签格式规则

### 标签命名规则

标签名必须符合以下规则：

- 必须以字母开头
- 只能包含字母、数字、下划线和连字符
- 大小写敏感

**有效示例：**

- `think`
- `tool_call`
- `tool-call`
- `ToolCall`
- `analysis123`

**无效示例：**

- `123tag`（以数字开头）
- `tag@name`（包含特殊字符）
- `tag name`（包含空格）

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

parser = StreamParser(tags={"think": "思考"})
for chunk in chunks:
    messages = parser.parse_chunk(chunk)
    for msg in messages:
        print(msg.content)  # 输出: "思考内容"
```

---

## 错误处理

### 标签验证错误

如果标签配置无效，会抛出 `ValueError`：

```python
from llm_stream_parser import StreamParser

try:
    parser = StreamParser(tags={"123tag": "步骤"})
except ValueError as e:
    print(f"标签配置错误: {e}")
```

### 常见错误

| 错误                                 | 原因               | 解决方法                       |
| ------------------------------------ | ------------------ | ------------------------------ |
| `ValueError: 标签名必须是非空字符串` | 标签名为空         | 提供有效的标签名               |
| `ValueError: 标签名 'xxx' 格式无效`  | 标签名包含非法字符 | 使用字母、数字、下划线或连字符 |
| `ValueError: 步骤名必须是非空字符串` | 步骤名为空         | 提供有效的步骤名               |

---

## 高级用法

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

messages = parser.parse_chunk("这是回答内容")
final = parser.finalize()
# final.step_name == "回答"
```

---

## 性能考虑

### 内存使用

- 解析器使用缓冲区来处理不完整的标签
- 对于非常大的流，建议定期调用 `finalize()` 或处理消息后清理

### 流式模式

- `enable_tags_streaming=True` 会产生更多消息，但提供更好的实时性
- `enable_tags_streaming=False` 会减少消息数量，但延迟更高

---

## 类型提示

完整的类型提示支持：

```python
from typing import AsyncGenerator, Dict, List, Optional
from llm_stream_parser import StreamParser, StreamMessage, process_llm_stream

# 类型注解
parser: StreamParser = StreamParser(tags={"think": "思考"})
messages: List[StreamMessage] = parser.parse_chunk("chunk")
stream: AsyncGenerator[StreamMessage, None] = process_llm_stream(async_stream(), tags)
```
