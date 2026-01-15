import asyncio
import re
from typing import AsyncGenerator, List, Optional, Dict, Tuple

from llm_stream_parser import StreamMessage


# 核心解析器类
class StreamParser:
    def __init__(self, tags: Optional[Dict[str, str]] = None, enable_tags_streaming: bool = False):
        """
        初始化流式解析器

        Args:
            tags: 标签字典，映射标签名到步骤名称
                 例如: {"think": "思考", "tool": "工具调用"}
                 如果为None或空字典，则不解析任何特殊标签
            enable_tags_streaming: 是否启用标签内流式输出
                             False（默认）: 等待标签结束后才输出完整内容
                             True: 实时输出流式内容和最终输出
        """
        # 验证和初始化标签
        self.tags = self._validate_tags(tags or {})
        self.enable_tags_streaming = enable_tags_streaming

        # 初始化基本状态
        self.buffer = ""
        self.current_state = "IDLE"
        self.current_content = ""
        self.step_counter = 0
        self.last_sent_content = ""
        # 用于跟踪每个step_name的step计数
        self.step_counters = {}

        # 动态生成状态和映射
        self.states = self._generate_states()
        self.tag_map = self._create_tag_map()
        self.tag_pattern = self._create_tag_pattern()

    def _validate_tags(self, tags: Dict[str, str]) -> Dict[str, str]:
        """
        验证标签配置的有效性

        Args:
            tags: 待验证的标签字典

        Returns:
            验证后的标签字典

        Raises:
            ValueError: 当标签配置无效时
        """
        validated_tags = {}

        for tag_name, step_name in tags.items():
            # 检查标签名
            if not tag_name or not isinstance(tag_name, str):
                raise ValueError(f"标签名必须是非空字符串，得到: {tag_name}")

            # 检查标签名格式（应该是有效的XML标签名）
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', tag_name):
                raise ValueError(f"标签名 '{tag_name}' 格式无效，应只包含字母、数字、下划线和连字符，且以字母开头")

            # 检查步骤名
            if not step_name or not isinstance(step_name, str):
                raise ValueError(f"步骤名必须是非空字符串，标签 '{tag_name}' 的步骤名为: {step_name}")

            validated_tags[tag_name] = step_name

        return validated_tags

    def _generate_states(self) -> Dict[str, str]:
        """
        动态生成状态常量

        Returns:
            状态字典，包含IDLE和每个标签对应的状态
        """
        states = {"IDLE": "IDLE"}

        for tag_name in self.tags.keys():
            state_name = f"IN_{tag_name.upper()}_BLOCK"
            states[state_name] = state_name

        return states

    def _create_tag_map(self) -> Dict[str, Tuple[str, str]]:
        """
        创建从标签名到(状态, 步骤名)的映射

        Returns:
            标签映射字典
        """
        tag_map = {}

        for tag_name, step_name in self.tags.items():
            state_name = f"IN_{tag_name.upper()}_BLOCK"
            tag_map[tag_name] = (self.states[state_name], step_name)

        return tag_map

    def _create_tag_pattern(self) -> re.Pattern:
        """
        创建用于匹配所有已知标签的正则表达式

        Returns:
            编译后的正则表达式模式
        """
        if not self.tags:
            # 如果没有定义任何标签，则创建一个永不匹配的正则
            return re.compile(r"(?!a)a")

        # 获取所有标签名并转义，以防标签名包含正则特殊字符
        known_tags = [re.escape(tag) for tag in self.tags.keys()]
        # 构建模式，例如: <(\/?)(think|tool|result)>
        tag_pattern_str = f"<(/?)({'|'.join(known_tags)})>"
        return re.compile(tag_pattern_str)

    def _generate_message(self, step_name: str, content: str, is_complete: bool = True) -> Optional[StreamMessage]:
        """
        内部方法：生成并返回一个 StreamMessage

        Args:
            step_name: 步骤名称
            content: 内容
            is_complete: 标签是否闭合（True表示闭合，False表示流式输出）

        Returns:
            生成的StreamMessage对象，如果内容为空则返回None
        """
        if not content:
            return None

        # 按step_name分组计数step
        if step_name not in self.step_counters:
            self.step_counters[step_name] = 0
        self.step_counters[step_name] += 1

        return StreamMessage(
            step=self.step_counters[step_name],
            step_name=step_name,
            content=content,
            is_complete=is_complete
        )

    def _maybe_emit_partial(self, messages: List[StreamMessage]) -> None:
        """
        如果内容有更新且启用了流式输出，则发送部分消息（只发送新增内容）。

        Args:
            messages: 要添加消息的列表
        """
        # 如果没有启用标签流式输出，且当前不在IDLE状态，则不发送部分消息
        if not self.enable_tags_streaming and self.current_state != "IDLE":
            return

        if self.current_content == self.last_sent_content:
            return

        # 计算新增内容（自上次发送以来的增量）
        # 只发送 current_content 中超出 last_sent_content 长度的部分
        last_len = len(self.last_sent_content)
        new_content = self.current_content[last_len:]

        if not new_content:
            return

        # 根据当前状态确定步骤名称和是否完整
        if self.current_state == "IDLE":
            step_name = "回答"
            is_complete = False  # IDLE状态下的内容也是流式的
        else:
            step_name = next(
                (name for state, name in self.tag_map.values() if state == self.current_state),
                "未知"
            )
            is_complete = False  # 标签块内的内容也是流式的

        message = self._generate_message(step_name, new_content, is_complete=is_complete)
        if message:
            messages.append(message)
            # 立即更新last_sent_content，避免重复发送
            self.last_sent_content = self.current_content

    def parse_chunk(self, chunk: str) -> List[StreamMessage]:
        """
        解析一个新的 chunk，返回一个或多个完整的 StreamMessage

        Args:
            chunk: 要解析的文本块

        Returns:
            解析出的StreamMessage列表
        """
        self.buffer += chunk
        messages = []
        last_pos = 0
        content_added = False  # 标记是否有新内容添加

        # 在缓冲区中查找所有完整的、我们关心的标签
        for match in self.tag_pattern.finditer(self.buffer):
            start, end = match.span()
            is_closing_tag = match.group(1) == '/'
            tag_name = match.group(2)

            # 1. 处理标签之前的文本内容
            text_before_tag = self.buffer[last_pos:start]
            if text_before_tag:
                self.current_content += text_before_tag
                content_added = True

            # 2. 处理标签本身，进行状态转换
            if is_closing_tag:
                expected_state, step_name = self.tag_map.get(tag_name, (None, None))
                if self.current_state == expected_state:
                    # 生成完整消息时，使用当前内容的完整副本
                    message = self._generate_message(step_name, self.current_content, is_complete=True)
                    if message:
                        messages.append(message)

                    self.current_state = "IDLE"
                    self.current_content = ""
                    self.last_sent_content = ""
                    content_added = False  # 重置标记，因为内容已经被处理
            else:
                # 在切换到新状态之前，先处理掉当前已经累积的内容
                if self.current_content:
                    if self.current_state == "IDLE":
                        step_name_for_old_content = "回答"
                    else:
                        # 如果当前在某个标签状态中，使用该标签的步骤名
                        step_name_for_old_content = next(
                            (name for state, name in self.tag_map.values() if state == self.current_state),
                            "回答"
                        )
                    # 生成完整消息时，使用当前内容的完整副本
                    message = self._generate_message(step_name_for_old_content, self.current_content, is_complete=True)
                    if message:
                        messages.append(message)

                new_state, step_name = self.tag_map.get(tag_name, ("IDLE", "回答"))
                self.current_state = new_state
                self.current_content = ""
                self.last_sent_content = ""
                content_added = False  # 重置标记，因为内容已经被处理

            last_pos = end

        # 3. 处理剩余的文本（没有匹配到标签的部分）
        remaining_text = self.buffer[last_pos:]

        # 4. 检查剩余内容是否可能是不完整的标签
        # 查找最后一个 '<' 的位置，它可能是不完整标签的开始
        potential_tag_start = remaining_text.rfind('<')

        if potential_tag_start >= 0:
            # 有可能是不完整的标签
            # 把 '<' 之前的内容加到 current_content
            safe_content = remaining_text[:potential_tag_start]
            if safe_content:
                self.current_content += safe_content
                content_added = True
            # 保留 '<' 及之后的内容在 buffer 中，等待下一个 chunk
            self.buffer = remaining_text[potential_tag_start:]
        else:
            # 没有可能是不完整的标签，把所有内容加到 current_content
            if remaining_text:
                self.current_content += remaining_text
                content_added = True
            self.buffer = ""

        # 5. 只在有新内容添加时才发送部分消息，避免重复
        if content_added:
            self._maybe_emit_partial(messages)

        return messages


    def finalize(self) -> Optional[StreamMessage]:
        """
        当流结束时，调用此方法处理缓冲区中剩余的内容

        Returns:
            最后的StreamMessage，如果没有内容则返回None
        """
        # 把 buffer 中剩余的内容加到 current_content
        if self.buffer:
            self.current_content += self.buffer
            self.buffer = ""

        # 计算新增内容（自上次发送以来的增量）
        last_len = len(self.last_sent_content)
        new_content = self.current_content[last_len:]

        # 如果没有新内容，返回 None
        if not new_content:
            return None

        if self.current_state == "IDLE":
            step_name = "回答"
        else:
            step_name = next(
                (name for state, name in self.tag_map.values() if state == self.current_state),
                "未知"
            )

        return self._generate_message(step_name, new_content, is_complete=True)


# 流式处理包装函数
async def process_llm_stream(
        stream: AsyncGenerator[str, None],
        tags: Optional[Dict[str, str]] = None
) -> AsyncGenerator[StreamMessage, None]:
    """
    处理LLM流式响应的包装函数

    Args:
        stream: 原始的文本流
        tags: 自定义标签字典，用于解析特定标签

    Yields:
        解析后的StreamMessage对象
    """
    parser = StreamParser(tags=tags)
    async for chunk in stream:
        messages = parser.parse_chunk(chunk)
        for message in messages:
            yield message
    final_message = parser.finalize()
    if final_message:
        yield final_message
