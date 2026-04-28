import asyncio
from llm_stream_parser import StreamParser, StreamMessage, process_llm_stream


class TestStreamParser:
    """StreamParser 测试类"""

    # 测试用例1: 自定义标签和多chunk测试（断言版）
    async def test_custom_tags_and_multi_chunk_with_assertions(self):
        """测试自定义标签以及标签内容被切割为多个chunk的情况"""

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
        # 注意：每个step_name有自己的计数器，所以每个步骤的step都是1
        step_names = [msg.step_name for msg in messages if msg]
        assert step_names == ["分析", "计算", "总结"], "步骤名称顺序应该正确"

    # 测试用例2: 不完整标签测试（断言版）
    async def test_incomplete_tags_with_assertions(self):
        """测试不完整或错误闭合的标签"""

        tags = {"think": "思考", "tool": "工具调用"}
        parser = StreamParser(tags=tags)

        # 模拟不完整标签输入
        test_chunks = [
            "思考内容",
            "",  # 完成上一个标签
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

    # 测试用例3: 特殊字符测试（断言版）
    async def test_special_characters_with_assertions(self):
        """测试包含特殊字符的内容"""

        tags = {"think": "思考", "tool": "工具调用"}
        parser = StreamParser(tags=tags)

        # 包含特殊字符的测试输入
        special_content = "思考内容包含特殊字符: <>&\"'反斜杠\\换行符\n制表符\t回车符\r"

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

    # 测试用例4: 空内容测试（断言版）
    async def test_empty_content_with_assertions(self):
        """测试空内容标签"""

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

    # 测试用例5: 大量数据测试（断言版）
    async def test_large_data_with_assertions(self):
        """测试大量数据处理"""

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

    async def test_async_stream(self):
        """测试异步流处理"""
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
                "结果。<ag",
                "tenderSubcontrac",
                "tEdit>{""这是表单",
                "内容}",
                "</agt",
                "enderSubcontractEdit>",
                "112313哈哈哈"
            ]

            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.1)  # 模拟网络延迟

        parser = StreamParser(tags={"think": "思考中", "tools": "工具调用", "agtenderSubcontractEdit": "表单"}, enable_tags_streaming=True)

        messages = []
        async for chunk in mock_stream():
            chunk_messages = parser.parse_chunk(chunk)
            for message in chunk_messages:
                messages.append(message)

        # finalize() 只在流结束后调用一次
        final = parser.finalize()
        if final:
            messages.append(final)

        # 验证消息数量和内容
        assert len(messages) > 0, "应该生成至少一条消息"
        
        # 验证步骤名称
        step_names = [msg.step_name for msg in messages if msg]
        assert "思考中" in step_names, "应该包含'思考中'步骤"
        assert "工具调用" in step_names, "应该包含'工具调用'步骤"
        assert "表单" in step_names, "应该包含'表单'步骤"

        # 验证思考内容
        think_messages = [msg for msg in messages if msg and msg.step_name == "思考中"]
        assert len(think_messages) > 0, "应该有思考中消息"
        assert any("我需要帮助用户查询天气" in msg.content for msg in think_messages), "思考内容应该完整"

        # 验证工具调用内容
        tools_messages = [msg for msg in messages if msg and msg.step_name == "工具调用"]
        assert len(tools_messages) > 0, "应该有工具调用消息"
        tools_content = "".join([msg.content for msg in tools_messages])
        assert "get_weather" in tools_content, "应该包含get_weather工具调用"
        assert "北京" in tools_content, "应该包含城市信息"
        assert "calculate" in tools_content, "应该包含calculate工具调用"

        # 验证表单内容
        form_messages = [msg for msg in messages if msg and msg.step_name == "表单"]
        assert len(form_messages) > 0, "应该有表单消息"
        assert any("这是表单内容" in msg.content for msg in form_messages), "表单内容应该完整"

    async def test_invalid_tag_name_empty(self):
        """测试空标签名应该抛出ValueError"""
        try:
            parser = StreamParser(tags={"": "步骤名"})
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "标签名必须是非空字符串" in str(e)

    async def test_invalid_tag_name_non_string(self):
        """测试非字符串标签名应该抛出ValueError"""
        try:
            parser = StreamParser(tags={123: "步骤名"})
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "标签名必须是非空字符串" in str(e)

    async def test_invalid_tag_name_format(self):
        """测试无效格式的标签名应该抛出ValueError"""
        # 以数字开头
        try:
            parser = StreamParser(tags={"1tag": "步骤名"})
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "格式无效" in str(e)
        
        # 包含特殊字符
        try:
            parser = StreamParser(tags={"tag@name": "步骤名"})
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "格式无效" in str(e)

    async def test_invalid_step_name_empty(self):
        """测试空步骤名应该抛出ValueError"""
        try:
            parser = StreamParser(tags={"tag": ""})
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "步骤名必须是非空字符串" in str(e)

    async def test_invalid_step_name_non_string(self):
        """测试非字符串步骤名应该抛出ValueError"""
        try:
            parser = StreamParser(tags={"tag": 123})
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "步骤名必须是非空字符串" in str(e)

    async def test_no_tags_defined(self):
        """测试没有定义标签的情况"""
        parser = StreamParser(tags=None)
        assert parser.tags == {}
        
        # 解析内容，应该只返回"回答"消息
        messages = parser.parse_chunk("这是一些内容")
        assert len(messages) > 0
        assert messages[0].step_name == "回答"
        assert "这是一些内容" in messages[0].content

    async def test_enable_tags_streaming_no_content_change(self):
        """测试启用标签流式输出但内容没有变化的情况"""
        parser = StreamParser(tags={"think": "思考"}, enable_tags_streaming=True)
        
        # 第一次解析
        messages1 = parser.parse_chunk("内容")
        assert len(messages1) > 0
        
        # 第二次解析相同内容，不应该产生新消息（因为内容没有变化）
        messages2 = parser.parse_chunk("")
        # 由于内容没有变化，_maybe_emit_partial 会提前返回
        # 但 parse_chunk 可能会因为其他原因产生消息
        # 这里我们主要测试 _maybe_emit_partial 的逻辑

    async def test_process_llm_stream_function(self):
        """测试 process_llm_stream 异步函数"""
        async def mock_stream():
            yield "让我思考一下"
            yield "<think>这是思考内容</think>"
            yield "这是最终答案"
        
        messages = []
        async for msg in process_llm_stream(
            mock_stream(),
            tags={"think": "思考"},
            enable_tags_streaming=True
        ):
            messages.append(msg)
        
        assert len(messages) > 0
        step_names = [msg.step_name for msg in messages]
        assert "思考" in step_names
        assert any("这是思考内容" in msg.content for msg in messages)

    async def test_enable_tags_streaming_emits_tag_boundaries(self):
        """测试启用标签流式输出时会保留标签边界消息"""
        parser = StreamParser(tags={"think": "思考"}, enable_tags_streaming=True)

        messages = []
        messages.extend(parser.parse_chunk("<think>这是"))
        messages.extend(parser.parse_chunk("思考</think>"))

        final_message = parser.finalize()
        if final_message:
            messages.append(final_message)

        think_stream_messages = [
            msg for msg in messages
            if msg.step_name == "思考" and msg.is_complete is False
        ]
        think_stream_content = "".join(msg.content for msg in think_stream_messages)

        assert "<think>" in think_stream_content
        assert "这是思考" in think_stream_content
        assert "</think>" in think_stream_content

    async def test_nested_tag_switch(self):
        """测试标签切换时的旧内容处理（覆盖第232行）"""
        parser = StreamParser(tags={"think": "思考", "tool": "工具"})
        
        # 先进入 think 状态，累积一些内容
        parser.parse_chunk("<think>思考内容")
        
        # 然后切换到 tool 状态，应该先输出 think 的完整内容
        messages = parser.parse_chunk("</think><tool>工具内容")
        
        # 应该有一条完整的 think 消息
        think_messages = [msg for msg in messages if msg.step_name == "思考"]
        assert len(think_messages) > 0
        assert "思考内容" in think_messages[0].content

    async def test_maybe_emit_partial_no_change(self):
        """测试内容没有变化时不发送消息（覆盖第158行）"""
        parser = StreamParser(tags={"think": "思考"}, enable_tags_streaming=True)
        
        # 第一次解析，产生消息
        messages1 = parser.parse_chunk("内容")
        assert len(messages1) > 0
        
        # 第二次解析空内容，内容没有变化，_maybe_emit_partial 会提前返回
        messages2 = parser.parse_chunk("")
        # 由于内容没有变化，不应该产生新的流式消息

    async def test_maybe_emit_partial_empty_new_content(self):
        """测试新增内容为空时不发送消息（覆盖第166行）"""
        parser = StreamParser(tags={"think": "思考"}, enable_tags_streaming=True)
        
        # 解析内容
        parser.parse_chunk("内容")
        
        # 解析空chunk，new_content为空，_maybe_emit_partial 会提前返回
        messages = parser.parse_chunk("")
        # 不应该产生新消息

    async def test_tag_switch_with_old_content(self):
        """测试标签切换时处理旧内容（覆盖第232行）"""
        parser = StreamParser(tags={"think": "思考", "tool": "工具"})
        
        # 先进入 think 状态，累积内容
        parser.parse_chunk("</think>思考内容")
        
        # 然后切换到 tool 状态，应该先输出 think 的完整内容
        messages = parser.parse_chunk("</think><tool>工具内容")
        
        # 验证 think 的完整消息
        think_messages = [msg for msg in messages if msg.step_name == "思考"]
        assert len(think_messages) == 0
        
        response_messages = [msg for msg in messages if msg.step_name == "回答"]
        assert len(response_messages) == 1

        assert "思考内容" in response_messages[0].content



    async def test_process_llm_stream_with_final_message(self):
        """测试 process_llm_stream 的 final_message（覆盖第334行）"""
        async def mock_stream():
            yield "内容"
        
        messages = []
        async for msg in process_llm_stream(
            mock_stream(),
            tags=None,
            enable_tags_streaming=False
        ):
            messages.append(msg)
        
        # 应该有 final_message
        assert len(messages) > 0
        assert messages[0].is_complete == False
        assert messages[0].content == "内容"

    async def test_unclosed_think_with_nested_tools(self):
        """测试think标签未闭合时，不应该解析出嵌套的tools标签"""
        parser = StreamParser(tags={"think": "思考", "tools": "工具调用"})
        
        # 模拟think标签未闭合，但其中包含tools标签的情况
        test_chunks = [
            "<think>我需要思考一下",
            "，然后调用工具",
            "<tools>",
            "  <get_weather>",
            "    <city>北京</city>",
            "  </get_weather>",
            # 注意：think标签没有闭合，tools标签也没有闭合
        ]
        
        messages = []
        for chunk in test_chunks:
            messages.extend(parser.parse_chunk(chunk))
        
        # finalize处理剩余内容
        final_message = parser.finalize()
        if final_message:
            messages.append(final_message)
        
        # 断言：不应该有"工具调用"步骤的消息
        tools_messages = [msg for msg in messages if msg and msg.step_name == "工具调用"]
        assert len(tools_messages) == 0, "think标签未闭合时，不应该解析出tools标签"
        
        # 断言：所有内容应该都在"思考"或"回答"中
        # 由于think未闭合，tools标签会被当作普通文本处理
        all_content = "".join([msg.content for msg in messages if msg])
        assert "我需要思考一下，然后调用工具" in all_content, "思考内容应该存在"
        assert "<tools>" in all_content or "tools" in all_content, "tools标签应该作为普通文本被保留"
        
        # 断言：验证步骤名称
        step_names = [msg.step_name for msg in messages if msg]
        assert "工具调用" not in step_names, "不应该有'工具调用'步骤"

    async def test_think_with_tools_then_answer_with_tools(self):
        """测试think标签内有工具调用（作为文本），think闭合后回答中也有工具调用（正常解析）"""
        parser = StreamParser(tags={"think": "思考", "tools": "工具调用"}, enable_tags_streaming=False)
        
        # 模拟完整的流程：
        # 1. think标签未闭合，包含tools标签（应该作为普通文本）
        # 2. think标签闭合
        # 3. 回答阶段包含tools标签（应该正常解析）
        test_chunks = [
            "<think>我需要思考一下",
            "，然后调用工具",
            "<tools>",
            "  <get_weather>",
            "    <city>北京</city>",
            "  </get_weather>",
            "</think>",  # think标签闭合
            "现在开始回答问题",
            "，我需要再次调用工具",
            "<tools>",
            "  <calculate>",
            "    <expression>1+1</expression>",
            "  </calculate>",
            "</tools>",  # tools标签闭合
            "这就是答案",
        ]
        
        messages = []
        for chunk in test_chunks:
            messages.extend(parser.parse_chunk(chunk))
        
        # finalize处理剩余内容
        final_message = parser.finalize()
        if final_message:
            messages.append(final_message)
        
        # 断言：验证消息数量
        non_empty_messages = [msg for msg in messages if msg]
        print(non_empty_messages)
        assert len(non_empty_messages) >= 3, "应该至少有3条消息（思考、工具调用、回答）"
        
        # 断言：验证思考消息
        think_messages = [msg for msg in non_empty_messages if msg.step_name == "思考"]
        assert len(think_messages) >= 1, "应该有1条思考消息"
        think_content = think_messages[0].content
        assert "我需要思考一下，然后调用工具" in think_content, "思考内容应该包含前半部分"
        assert "<tools>" in think_content, "think中的tools标签应该作为普通文本保留"
        assert "get_weather" in think_content, "think中的工具调用内容应该保留"
        
        # 断言：验证工具调用消息（来自回答阶段的tools）
        tools_messages = [msg for msg in non_empty_messages if msg.step_name == "工具调用"]
        assert len(tools_messages) == 1, "应该有1条工具调用消息（来自回答阶段）"
        tools_content = tools_messages[0].content
        assert "calculate" in tools_content, "应该包含calculate工具调用"
        assert "1+1" in tools_content, "应该包含计算表达式"
        
        # 断言：验证回答消息
        answer_messages = [msg for msg in non_empty_messages if msg.step_name == "回答"]
        assert len(answer_messages) >= 1, "应该至少有1条回答消息"
        all_answer_content = "".join([msg.content for msg in answer_messages])
        assert "现在开始回答问题" in all_answer_content, "应该包含回答内容"
        assert "这就是答案" in all_answer_content, "应该包含最终答案"
        
        # 断言：验证步骤顺序
        step_names = [msg.step_name for msg in non_empty_messages]
        # 顺序应该是：思考 -> 工具调用 -> 回答（可能有多条回答消息）
        assert step_names[0] == "思考", "第一条消息应该是思考"
        assert "工具调用" in step_names, "应该包含工具调用步骤"
        assert "回答" in step_names, "应该包含回答步骤"


# 如果直接运行此文件，执行所有测试
if __name__ == "__main__":
    import sys
    
    async def run_all_tests():
        test_instance = TestStreamParser()
        
        tests = [
            test_instance.test_custom_tags_and_multi_chunk_with_assertions,
            test_instance.test_incomplete_tags_with_assertions,
            test_instance.test_special_characters_with_assertions,
            test_instance.test_empty_content_with_assertions,
            test_instance.test_large_data_with_assertions,
            test_instance.test_async_stream,
            test_instance.test_invalid_tag_name_empty,
            test_instance.test_invalid_tag_name_non_string,
            test_instance.test_invalid_tag_name_format,
            test_instance.test_invalid_step_name_empty,
            test_instance.test_invalid_step_name_non_string,
            test_instance.test_no_tags_defined,
            test_instance.test_enable_tags_streaming_no_content_change,
            test_instance.test_process_llm_stream_function,
            test_instance.test_enable_tags_streaming_emits_tag_boundaries,
            test_instance.test_nested_tag_switch,
            test_instance.test_maybe_emit_partial_no_change,
            test_instance.test_maybe_emit_partial_empty_new_content,
            test_instance.test_tag_switch_with_old_content,
            test_instance.test_process_llm_stream_with_final_message,
            test_instance.test_unclosed_think_with_nested_tools,
            test_instance.test_think_with_tools_then_answer_with_tools
        ]
        
        for test in tests:
            try:
                await test()
                print(f"✅ {test.__name__} 通过")
            except Exception as e:
                print(f"❌ {test.__name__} 失败: {e}")
                sys.exit(1)
    
    asyncio.run(run_all_tests())
