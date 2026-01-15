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


# 新增测试用例1: 自定义标签和多chunk测试（断言版）
async def test_custom_tags_and_multi_chunk_with_assertions():
    """测试自定义标签以及标签内容被切割为多个chunk的情况"""
    print("=== 测试自定义标签和多chunk（断言版） ===")

    # 定义自定义标签
    custom_tags = {
        "analysis": "分析",
        "calculation": "计算",
        "summary": "总结"
    }

    parser = StreamParser(tags=custom_tags)

    # 模拟标签内容被切割成多个chunk的情况
    test_chunks = [
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
    for chunk in test_chunks:
        messages.extend(parser.parse_chunk(chunk))

    final_message = parser.finalize()
    if final_message:
        messages.append(final_message)

    assert messages[0].step_name == "分析", "步骤名称应该是'分析'"
    assert messages[0].content == "这是分析内容的第一部分，这是第二部分", "步骤内容错误"
    assert messages[1].step_name == "计算", "步骤名称应该是'计算'"
    assert messages[1].content == "计算过程：1+1=2", "步骤内容错误"
    assert messages[2].step_name == "总结", "步骤名称应该是'总结'"
    assert messages[2].content == "总结内容在多个chunk中", "步骤内容错误"

    # 断言：确保生成了正确的消息数量
    assert len([msg for msg in messages if msg]) == 3, "应该生成3条消息"

    # 断言：验证分析消息
    analysis_msg = next((msg for msg in messages if msg and msg.step_name == "分析"), None)
    assert analysis_msg is not None, "应该包含分析消息"
    assert "这是分析内容的第一部分，这是第二部分" in analysis_msg.content, "分析内容应该完整"

    # 断言：验证计算消息
    calculation_msg = next((msg for msg in messages if msg and msg.step_name == "计算"), None)
    assert calculation_msg is not None, "应该包含计算消息"
    assert "计算过程：1+1=2" in calculation_msg.content, "计算内容应该完整"

    # 断言：验证总结消息
    summary_msg = next((msg for msg in messages if msg and msg.step_name == "总结"), None)
    assert summary_msg is not None, "应该包含总结消息"
    assert "总结内容在多个chunk中" in summary_msg.content, "总结内容应该完整"

    # 断言：验证步骤计数
    steps = [msg.step for msg in messages if msg]
    assert steps == [1, 2, 3], "步骤计数应该连续"

    print("✅ 自定义标签和多chunk测试通过")


# 新增测试用例2: 不完整标签测试（断言版）
async def test_incomplete_tags_with_assertions():
    """测试不完整或错误闭合的标签"""
    print("=== 测试不完整标签（断言版） ===")

    tags = {"think": "思考", "tool": "工具调用"}
    parser = StreamParser(tags=tags)

    # 模拟不完整标签输入
    test_chunks = [
        "<think>思考内容",
        "</think>",  # 完成上一个标签
        "<tool>工具调用",
        "继续内容",  # 没有正确闭合
        "最后内容"
    ]

    messages = []
    for chunk in test_chunks:
        messages.extend(parser.parse_chunk(chunk))

    final_message = parser.finalize()
    if final_message:
        messages.append(final_message)

    # 断言：确保生成了消息
    assert len(messages) > 0, "应该生成至少一条消息"

    # 断言：检查是否有"思考内容"相关消息
    assert any("思考内容" in msg.content for msg in messages), "应该包含思考内容"

    # 断言：检查是否有未闭合标签的内容
    assert any("工具调用继续内容" in msg.content or "最后内容" in msg.content for msg in messages), "应该处理未闭合标签的内容"

    # 断言：验证步骤名称
    step_names = [msg.step_name for msg in messages if msg]
    assert "思考" in step_names or "工具调用" in step_names, "应该包含预定义的步骤名称"
    print("✅ 不完整标签测试通过")


# 新增测试用例3: 特殊字符测试（断言版）
async def test_special_characters_with_assertions():
    """测试包含特殊字符的内容"""
    print("=== 测试特殊字符（断言版） ===")

    tags = {"think": "思考", "tool": "工具调用"}
    parser = StreamParser(tags=tags)

    # 包含特殊字符的测试输入
    special_content = "<think>思考内容包含特殊字符: <>&\"'反斜杠\\换行符\n制表符\t回车符\r</think>"

    messages = []
    for chunk in [special_content[i:i + 10] for i in range(0, len(special_content), 10)]:
        messages.extend(parser.parse_chunk(chunk))

    final_message = parser.finalize()
    if final_message:
        messages.append(final_message)

    # 断言：确保生成了消息
    assert len(messages) > 0, "应该生成至少一条消息"

    # 断言：检查特殊字符是否被正确处理
    content_combined = "".join([msg.content for msg in messages if msg])
    assert "<>&\"'反斜杠\\" in content_combined, "特殊字符应该被正确保留"
    assert "\n" in content_combined or "\\n" in content_combined, "换行符应该被正确处理"
    assert "\t" in content_combined or "\\t" in content_combined, "制表符应该被正确处理"

    # 断言：验证步骤名称正确
    for msg in messages:
        if msg:
            assert msg.step_name in ["思考", "工具调用", "回答"], f"步骤名称'{msg.step_name}'应该是预定义值之一"

    print("✅ 特殊字符测试通过")


# 新增测试用例4: 空内容测试（断言版）
async def test_empty_content_with_assertions():
    """测试空内容标签"""
    print("=== 测试空内容（断言版） ===")

    tags = {"think": "思考", "tool": "工具调用"}
    parser = StreamParser(tags=tags)

    # 空内容测试
    test_input = "<think></think><tool>非空内容</tool>"

    messages = parser.parse_chunk(test_input)
    final_message = parser.finalize()
    if final_message:
        messages.append(final_message)
    # 断言：确保至少有一条消息（来自非空的tool标签）
    assert len([msg for msg in messages if msg]) >= 1, "应该至少生成一条非空消息"

    # 断言：检查是否包含非空内容
    non_empty_messages = [msg for msg in messages if msg and msg.content.strip()]
    assert len(non_empty_messages) >= 1, "应该至少有一条包含实际内容的消息"
    assert any("非空内容" in msg.content for msg in non_empty_messages), "应该包含'非空内容'"

    # 断言：空标签不应该生成消息
    empty_messages = [msg for msg in messages if msg and not msg.content.strip()]
    # 注意：当前实现中空内容不会生成消息，所以这里不需要特别检查

    print("✅ 空内容测试通过")


# 新增测试用例5: 大量数据测试（断言版）
async def test_large_data_with_assertions():
    """测试大量数据处理"""
    print("=== 测试大量数据（断言版） ===")

    tags = {"think": "思考", "tool": "工具调用"}
    parser = StreamParser(tags=tags)

    # 生成大量数据
    large_content = "<think>" + "大量重复的思考内容 " * 1000 + "</think>"

    messages = []
    # 分小块处理大量数据
    chunk_size = 50
    for i in range(0, len(large_content), chunk_size):
        chunk = large_content[i:i + chunk_size]
        messages.extend(parser.parse_chunk(chunk))

    final_message = parser.finalize()
    if final_message:
        messages.append(final_message)

    # 断言：确保只生成了一条消息（因为只有一个完整的标签块）
    assert len([msg for msg in messages if msg]) == 1, "应该只生成一条消息"

    # 断言：验证消息内容长度
    if messages and messages[0]:
        content_length = len(messages[0].content)
        expected_min_length = len("大量重复的思考内容 ") * 1000
        assert content_length >= expected_min_length, f"内容长度({content_length})应该至少为{expected_min_length}"

    # 断言：验证步骤信息
    if messages and messages[0]:
        msg = messages[0]
        assert msg.step == 1, "步骤号应该是1"
        assert msg.step_name == "思考", "步骤名称应该是'思考'"

    print("✅ 大量数据测试通过")


async def test_async_stream():
    # 模拟流式响应
    async def mock_stream():
        chunks = [
            "<think>我需要帮",
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
            "结果。<ag"
            "tenderSubcontrac",
            "tEdit>{”“这是表单",
            "内容}",
            "</agt",
            "enderSubcontractEdit>",
            "112313哈哈哈"
        ]

        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.1)  # 模拟网络延迟

    parser = StreamParser(tags={"think": "思考中", "tools": "工具调用", "agtenderSubcontractEdit": "表单"}, enable_tags_streaming=True)

    async for chunk in mock_stream():
        messages = parser.parse_chunk(chunk)
        for message in messages:
            print(message)

    # finalize() 只在流结束后调用一次
    final = parser.finalize()
    if final:
        print(final)


if __name__ == "__main__":
    asyncio.run(test_async_stream())
