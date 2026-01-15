"""
LLM Stream Parser - Real-time parser for LLM streaming responses

A Python library for parsing streaming LLM responses with tag-based content extraction.
Supports real-time parsing of structured content embedded in streaming text.
"""


__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "StreamParser",
    "process_llm_stream",
    "StreamMessage",
]

from llm_stream_parser.models import StreamMessage
from llm_stream_parser.parser import StreamParser, process_llm_stream
