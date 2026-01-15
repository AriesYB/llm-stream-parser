# LLM Stream Parser

[![Tests](https://github.com/AriesYB/llm-stream-parser/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/AriesYB/llm-stream-parser/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/llm-stream-parser)](https://pypi.org/project/llm-stream-parser/)
[![Python](https://img.shields.io/pypi/pyversions/llm-stream-parser)](https://pypi.org/project/llm-stream-parser/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个用于实时解析大语言模型（LLM）流式响应的 Python 库，支持基于 XML 标签提取内容。

## 📦 安装

### 使用 pip 安装

```bash
pip install llm-stream-parser
```

### 使用 uv 安装

```bash
uv add llm-stream-parser
```

## 🚀 快速开始

### 解析自定义标签

解析器会自动处理标签和内容被分割到多个 chunk 的情况：

```python
from llm_stream_parser import StreamParser

# 定义自定义标签（支持多个标签）
custom_tags = {
    "analysis": "分析",
    "calculation": "计算",
    "summary": "总结"
}

parser = StreamParser(tags=custom_tags)

# 模拟标签内容被切割成多个 chunk 的场景
chunks = [
    "<anal",           # 标签被分割
    "ysis>这是分析内容的第一部分",
    "，这是第二部分</a",
    "nalysis>",        # 标签闭合
    "<calcu",
    "lation>计算过程：1+1=",
    "2</calc",
    "ulation>",
    "<sum",
    "mary>总结内容在",
    "多个chunk中</summar",
    "y>"
]

# 逐块解析
messages = []
for chunk in chunks:
    messages.extend(parser.parse_chunk(chunk))

# 处理流结束后的剩余内容
final = parser.finalize()
if final:
    messages.append(final)

# 输出结果
for msg in messages:
    print(f"{msg.step_name}: {msg.content}")
```

**输出**：

```
分析: 这是分析内容的第一部分，这是第二部分
计算: 计算过程：1+1=2
总结: 总结内容在多个chunk中
```

### 实时流式输出（enable_tags_streaming）

启用 `enable_tags_streaming` 后，标签内的内容会实时输出，待标签闭合再输出一条完整内容，而不是等待标签闭合：

```python
from llm_stream_parser import StreamParser

# 启用标签内内容的实时流式输出
parser = StreamParser(
    tags={"think": "思考中", "tools": "工具调用"},
    enable_tags_streaming=True  # 关键参数：启用标签内内容流式输出
)

# 模拟 LLM 流式输出
chunks = [
    "<think>让我思考",
    "一下...",
    "正在分析",
    "问题...</think>",
    "需要调用工具：<tools>",
    "<get_weather>",
    "北京",
    "</get_weather>",
    "</tools>",
    "这是最终答案。"
]

for chunk in chunks:
    for msg in parser.parse_chunk(chunk):
        # is_complete=False 表示标签未闭合（流式输出中）
        print(f"{msg.step_name}: {msg.content} [标签闭合: {msg.is_complete}]")
```

**输出**：

```
思考中: 让我思考 [标签闭合: False]
思考中: 一下... [标签闭合: False]
思考中: 正在分析 [标签闭合: False]
思考中: 让我思考一下...正在分析问题... [标签闭合: True]
回答: 需要调用工具： [标签闭合: True]
工具调用: <get_weather>北京 [标签闭合: False]
工具调用: <get_weather>北京</get_weather> [标签闭合: True]
回答: 这是最终答案。 [标签闭合: False]
```

### 集成方法 process_llm_stream

直接对接 llm 异步流式输出

```python
import asyncio
from llm_stream_parser import process_llm_stream

async def main():
    # 模拟 LLM 流式响应
    async def mock_stream():
        yield "让我分析一下..."
        yield "<analysis>这是分析内容</analysis>"
        yield "这是最终答案。"

    # 封装异步流式输出
    async for msg in process_llm_stream(
            mock_stream(),
            tags={"analysis": "分析"},
            enable_tags_streaming=True
    ):
        print(f"{msg.step_name}: {msg.content} [标签闭合: {msg.is_complete}]")

asyncio.run(main())
```

**输出**

```
回答: 让我分析一下... [标签闭合: False]
回答: 让我分析一下... [标签闭合: True]
分析: 这是分析内容 [标签闭合: True]
回答: 这是最终答案。 [标签闭合: False]
```

## 🎯 使用场景

### 1. 展示模型执行多步骤任务时的状态

```python
parser = StreamParser(tags={
    "analysis": "分析",
    "planning": "规划",
    "execution": "执行",
    "summary": "总结"
})

# LLM 输出包含多个标签，可以按步骤实时展示行为
```

### 2. 基于 xml 的工具调用解析

```python
parser = StreamParser(tags={
    "tools": "工具调用",
})

# LLM 输出: "我需要查询天气。<tool>get_weather(city='北京')</tool>"
# 解析后可以分别处理工具调用和结果
```
