"""
Data models for LLM Stream Parser
"""

from typing import Any

from pydantic import BaseModel, Field


class StreamMessage(BaseModel):
    """
    Represents a parsed message from the streaming LLM response.

    Attributes:
        step: Step number (auto-incremented per step_name)
        step_name: Name of the step (e.g., "思考", "工具调用", "回答")
        title: Optional title for the message
        content: The content of the message
        is_complete: Whether the tag is closed (True) or still streaming (False)
    """
    step: int = Field(..., description="步骤序号")
    step_name: str = Field(..., description="步骤名称")
    title: str = Field(default="", description="标题")
    content: Any = Field(..., description="内容")
    is_complete: bool = Field(default=True, description="标签是否闭合（True表示闭合，False表示流式输出）")
