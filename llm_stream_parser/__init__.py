"""
LLM Stream Parser - Real-time parser for LLM streaming responses

A Python library for parsing streaming LLM responses with tag-based content extraction.
Supports real-time parsing of structured content embedded in streaming text.
"""


__version__ = "0.1.2"
__author__ = "AriesYB"
__email__ = "37505429+AriesYB@users.noreply.github.com"

__all__ = [
    "StreamParser",
    "process_llm_stream",
    "StreamMessage",
]

from llm_stream_parser.models import StreamMessage
from llm_stream_parser.parser import StreamParser, process_llm_stream
