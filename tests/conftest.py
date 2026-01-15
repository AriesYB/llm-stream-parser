"""
Pytest fixtures for LLM Stream Parser tests
"""

import pytest
from llm_stream_parser import StreamParser


@pytest.fixture
def basic_parser():
    """Create a basic parser with common tags."""
    return StreamParser(tags={"think": "思考", "tool": "工具"})


@pytest.fixture
def streaming_parser():
    """Create a parser with streaming enabled."""
    return StreamParser(
        tags={"think": "思考"},
        enable_tags_streaming=True
    )


@pytest.fixture
def custom_tags_parser():
    """Create a parser with custom tags."""
    return StreamParser(tags={
        "analysis": "分析",
        "calculation": "计算",
        "summary": "总结"
    })
