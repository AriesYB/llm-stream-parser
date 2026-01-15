"""
Async tests for StreamParser
"""

import asyncio
import pytest
from llm_stream_parser import StreamParser, process_llm_stream


class TestAsyncProcessing:
    """Test async stream processing."""

    @pytest.mark.asyncio
    async def test_process_llm_stream_basic(self):
        """Test basic async stream processing."""
        async def mock_stream():
            yield "</think>思考内容</think>"
            yield "回答内容"

        tags = {"think": "思考"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        assert len(messages) >= 2
        assert any(msg.step_name == "思考" for msg in messages)
        assert any(msg.step_name == "回答" for msg in messages)

    @pytest.mark.asyncio
    async def test_process_llm_stream_with_streaming(self):
        """Test async stream processing with streaming enabled."""
        async def mock_stream():
            yield "</think>思考"
            yield "内容"
            yield "</think>"
            yield "回答内容"

        tags = {"think": "思考"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags, enable_tags_streaming=True):
            messages.append(msg)

        # Should have partial messages in streaming mode
        assert len(messages) > 0
        assert any(not msg.is_complete for msg in messages)

    @pytest.mark.asyncio
    async def test_process_llm_stream_multi_chunk(self):
        """Test async stream processing with multiple chunks."""
        async def mock_stream():
            chunks = [
                "</think>我需要帮",
                "助用户查",
                "询天气</think>",
                "我需要帮",
                "您查询天",
                "气信息。<tools>",
                "\n<get_wea",
                "ther>\n  <city>北京</city>",
                "\n  <unit>celsius</unit>",
                "\n</get_weather>",
                "\n\n同时，我也会进行一些计算：",
                "\n<calculate>",
                "\n  <expression>100 / 5</expression>",
                "\n</calculate>",
                "\n</to",
                "ols>",
                "\n\n这就是全部",
                "结果。"
            ]
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.01)  # Simulate network delay

        tags = {"think": "思考中", "tools": "工具调用"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        assert len(messages) > 0
        assert any(msg.step_name == "思考中" for msg in messages)
        assert any(msg.step_name == "工具调用" for msg in messages)

    @pytest.mark.asyncio
    async def test_process_llm_stream_empty(self):
        """Test async stream processing with empty stream."""
        async def mock_stream():
            return
            yield  # Make it a generator

        tags = {"think": "思考"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_process_llm_stream_no_tags(self):
        """Test async stream processing with no tags."""
        async def mock_stream():
            yield "这是回答内容"
            yield "这是更多回答"

        messages = []
        async for msg in process_llm_stream(mock_stream(), tags=None):
            messages.append(msg)

        assert len(messages) >= 1
        assert all(msg.step_name == "回答" for msg in messages)

    @pytest.mark.asyncio
    async def test_process_llm_stream_custom_tags(self):
        """Test async stream processing with custom tags."""
        async def mock_stream():
            yield "<analysis>分析内容</analysis>"
            yield "<calculation>计算结果</calculation>"
            yield "<summary>总结内容</summary>"

        tags = {
            "analysis": "分析",
            "calculation": "计算",
            "summary": "总结"
        }
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        assert len(messages) == 3
        assert messages[0].step_name == "分析"
        assert messages[1].step_name == "计算"
        assert messages[2].step_name == "总结"

    @pytest.mark.asyncio
    async def test_process_llm_stream_incomplete_tag(self):
        """Test async stream processing with incomplete tag."""
        async def mock_stream():
            yield "</think>思考内容"
            # Tag never closes

        tags = {"think": "思考"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        # Finalize should handle incomplete tag
        assert len(messages) >= 1
        assert any("思考内容" in msg.content for msg in messages)

    @pytest.mark.asyncio
    async def test_process_llm_stream_special_characters(self):
        """Test async stream processing with special characters."""
        async def mock_stream():
            yield "</think>特殊字符: <>&\"'\\n\\t\\r</think>"

        tags = {"think": "思考"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        assert len(messages) >= 1
        content = "".join([msg.content for msg in messages])
        assert "<>&\"'" in content

    @pytest.mark.asyncio
    async def test_process_llm_stream_large_data(self):
        """Test async stream processing with large data."""
        async def mock_stream():
            large_content = "</think>" + "大量内容 " * 1000 + "</think>"
            chunk_size = 100
            for i in range(0, len(large_content), chunk_size):
                yield large_content[i:i + chunk_size]
                await asyncio.sleep(0.001)

        tags = {"think": "思考"}
        messages = []
        async for msg in process_llm_stream(mock_stream(), tags):
            messages.append(msg)

        assert len(messages) >= 1
        assert any(len(msg.content) > 1000 for msg in messages)
