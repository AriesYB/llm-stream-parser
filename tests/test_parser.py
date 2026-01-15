"""
Unit tests for StreamParser
"""

import pytest
from llm_stream_parser import StreamParser, StreamMessage


class TestBasicParsing:
    """Test basic parsing functionality."""

    def test_simple_tag_parsing(self, basic_parser):
        """Test parsing a simple tag."""
        chunk = "</think>思考内容</think>"
        messages = basic_parser.parse_chunk(chunk)
        assert len(messages) == 1
        assert messages[0].step_name == "思考"
        assert messages[0].content == "思考内容"
        assert messages[0].is_complete is True

    def test_multiple_tags(self, basic_parser):
        """Test parsing multiple tags."""
        chunk = "</think>思考1</think><tool>工具调用</tool>"
        messages = basic_parser.parse_chunk(chunk)
        assert len(messages) == 2
        assert messages[0].step_name == "思考"
        assert messages[1].step_name == "工具"

    def test_text_without_tags(self, basic_parser):
        """Test parsing text without any tags."""
        chunk = "这是普通文本"
        messages = basic_parser.parse_chunk(chunk)
        final = basic_parser.finalize()
        assert len(messages) == 0
        assert final is not None
        assert final.step_name == "回答"
        assert final.content == "这是普通文本"

    def test_empty_chunk(self, basic_parser):
        """Test parsing an empty chunk."""
        messages = basic_parser.parse_chunk("")
        assert len(messages) == 0


class TestMultiChunkParsing:
    """Test parsing across multiple chunks."""

    def test_tag_split_across_chunks(self, basic_parser):
        """Test when a tag is split across multiple chunks."""
        chunks = ["<th", "ink>思考内容</", "think>"]
        messages = []
        for chunk in chunks:
            messages.extend(basic_parser.parse_chunk(chunk))
        assert len(messages) == 1
        assert messages[0].content == "思考内容"

    def test_content_split_across_chunks(self, basic_parser):
        """Test when content is split across multiple chunks."""
        chunks = [""]
        messages = []
        for chunk in chunks:
            messages.extend(basic_parser.parse_chunk(chunk))
        assert len(messages) == 1
        assert messages[0].content == "思考内容"

    def test_complex_multi_chunk_scenario(self, custom_tags_parser):
        """Test complex scenario with multiple tags split across chunks."""
        chunks = [
            "<anal",
            "ysis>这是分析内容的第一部分",
            "，这是第二部分</a",
            "nalysis>",
            "<calcu",
            "lation>计算过程：1+1=",
            "2</calc",
            "ulation>",
            "<sum",
            "mary>总结内容在",
            "多个chunk中</summar",
            "y>"
        ]
        messages = []
        for chunk in chunks:
            messages.extend(custom_tags_parser.parse_chunk(chunk))
        final = custom_tags_parser.finalize()
        if final:
            messages.append(final)

        assert len([msg for msg in messages if msg]) == 3
        assert messages[0].step_name == "分析"
        assert messages[0].content == "这是分析内容的第一部分，这是第二部分"
        assert messages[1].step_name == "计算"
        assert messages[1].content == "计算过程：1+1=2"
        assert messages[2].step_name == "总结"
        assert messages[2].content == "总结内容在多个chunk中"


class TestStreamingMode:
    """Test streaming output mode."""

    def test_streaming_mode_enabled(self, streaming_parser):
        """Test that streaming mode emits partial messages."""
        chunks = ["<think>思考", "内容</think>"]
        messages = []
        for chunk in chunks:
            messages.extend(streaming_parser.parse_chunk(chunk))
        # Should have partial messages in streaming mode
        assert len(messages) > 0
        # Check that at least one message is incomplete
        assert any(not msg.is_complete for msg in messages)

    def test_streaming_mode_disabled(self, basic_parser):
        """Test that non-streaming mode waits for tag close."""
        chunks = ["<think>思考", "内容</think>"]
        messages = []
        for chunk in chunks:
            messages.extend(basic_parser.parse_chunk(chunk))
        # Should only have complete messages
        assert all(msg.is_complete for msg in messages)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_incomplete_tag(self, basic_parser):
        """Test handling of incomplete tags."""
        chunk = "<think>思考内容"
        messages = basic_parser.parse_chunk(chunk)
        final = basic_parser.finalize()
        assert len(messages) == 0
        assert final is not None
        assert "思考内容" in final.content

    def test_empty_tag_content(self, basic_parser):
        """Test handling of empty tag content."""
        chunk = "<think></think><tool>非空内容</tool>"
        messages = basic_parser.parse_chunk(chunk)
        non_empty_messages = [msg for msg in messages if msg and msg.content.strip()]
        assert len(non_empty_messages) == 1
        assert "非空内容" in non_empty_messages[0].content

    def test_special_characters(self, basic_parser):
        """Test handling of special characters."""
        special_content = "</think>思考内容包含特殊字符: <>&\"'反斜杠\\换行符\n制表符\t回车符\r</think>"
        messages = []
        for i in range(0, len(special_content), 10):
            chunk = special_content[i:i + 10]
            messages.extend(basic_parser.parse_chunk(chunk))
        final = basic_parser.finalize()
        if final:
            messages.append(final)

        assert len(messages) > 0
        content_combined = "".join([msg.content for msg in messages if msg])
        assert "<>&\"'反斜杠\\" in content_combined

    def test_large_data(self, basic_parser):
        """Test handling of large amounts of data."""
        large_content = "</think>" + "大量重复的思考内容 " * 1000 + "</think>"
        messages = []
        chunk_size = 50
        for i in range(0, len(large_content), chunk_size):
            chunk = large_content[i:i + chunk_size]
            messages.extend(basic_parser.parse_chunk(chunk))
        final = basic_parser.finalize()
        if final:
            messages.append(final)

        assert len([msg for msg in messages if msg]) == 1
        if messages and messages[0]:
            assert len(messages[0].content) >= len("大量重复的思考内容 ") * 1000

    def test_nested_tags(self, basic_parser):
        """Test handling of nested tags (should be treated as separate)."""
        chunk = "<think>外层<tool>内层</tool>外层结束</think>"
        messages = basic_parser.parse_chunk(chunk)
        # Should parse both tags separately
        assert len(messages) >= 2


class TestTagValidation:
    """Test tag validation."""

    def test_invalid_tag_name(self):
        """Test that invalid tag names raise ValueError."""
        with pytest.raises(ValueError):
            StreamParser(tags={"123tag": "步骤"})

    def test_invalid_tag_name_with_special_chars(self):
        """Test that tag names with special characters raise ValueError."""
        with pytest.raises(ValueError):
            StreamParser(tags={"tag@name": "步骤"})

    def test_empty_tag_name(self):
        """Test that empty tag names raise ValueError."""
        with pytest.raises(ValueError):
            StreamParser(tags={"": "步骤"})

    def test_empty_step_name(self):
        """Test that empty step names raise ValueError."""
        with pytest.raises(ValueError):
            StreamParser(tags={"think": ""})

    def test_valid_tag_names(self):
        """Test that valid tag names are accepted."""
        parser = StreamParser(tags={
            "think": "思考",
            "tool_call": "工具调用",
            "tool-call": "工具调用",
            "ToolCall": "工具调用"
        })
        assert len(parser.tags) == 4


class TestStepCounting:
    """Test step counting functionality."""

    def test_step_counter_per_step_name(self, basic_parser):
        """Test that step counters are maintained per step name."""
        chunk = "</think>思考1</think><tool>工具1</tool></think>思考2</think><tool>工具2</tool>"
        messages = basic_parser.parse_chunk(chunk)
        think_messages = [msg for msg in messages if msg.step_name == "思考"]
        tool_messages = [msg for msg in messages if msg.step_name == "工具"]
        assert think_messages[0].step == 1
        assert think_messages[1].step == 2
        assert tool_messages[0].step == 1
        assert tool_messages[1].step == 2

    def test_step_counter_with_finalize(self, basic_parser):
        """Test step counting with finalize."""
        chunk = "回答内容"
        messages = basic_parser.parse_chunk(chunk)
        final = basic_parser.finalize()
        assert final is not None
        assert final.step == 1
        assert final.step_name == "回答"


class TestFinalize:
    """Test finalize functionality."""

    def test_finalize_with_remaining_content(self, basic_parser):
        """Test finalize with content remaining in buffer."""
        chunk = "回答内容"
        messages = basic_parser.parse_chunk(chunk)
        final = basic_parser.finalize()
        assert len(messages) == 0
        assert final is not None
        assert final.content == "回答内容"
        assert final.is_complete is True

    def test_finalize_with_no_content(self, basic_parser):
        """Test finalize when there's no content."""
        final = basic_parser.finalize()
        assert final is None

    def test_finalize_after_complete_parse(self, basic_parser):
        """Test finalize after all content has been parsed."""
        chunk = "</think>思考内容</think>"
        messages = basic_parser.parse_chunk(chunk)
        final = basic_parser.finalize()
        assert len(messages) == 1
        assert final is None


class TestNoTagsMode:
    """Test parser with no tags configured."""

    def test_no_tags_mode(self):
        """Test parser with no tags - all content is treated as answer."""
        parser = StreamParser(tags=None)
        chunk = "这是回答内容"
        messages = parser.parse_chunk(chunk)
        final = parser.finalize()
        assert len(messages) == 0
        assert final is not None
        assert final.step_name == "回答"
        assert final.content == "这是回答内容"

    def test_no_tags_with_angle_brackets(self):
        """Test that angle brackets are treated as regular text when no tags."""
        parser = StreamParser(tags=None)
        chunk = "这是<普通>文本"
        messages = parser.parse_chunk(chunk)
        final = parser.finalize()
        assert final is not None
        assert "这是<普通>文本" in final.content
