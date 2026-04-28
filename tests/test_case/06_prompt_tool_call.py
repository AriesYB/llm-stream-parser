"""
示例9: 基于XML标签提示词的工具调用（异步流式版本）
演示如何使用自定义的 @llm_tool 注解定义工具，通过XML标签识别工具调用
这种方式不依赖大模型的 function call 能力 (Deepseek R1 不支持function call)，且支持流式输出解析
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

# 加载 .env 文件
load_dotenv()

from tools import llm_tool, LLMToolIntegration, StreamMessage


def init_llm():
    """初始化模型（禁用 function call，使用纯文本模式）"""
    return ChatOpenAI(
        model="deepseek-r1",
        temperature=0.3,
        streaming=True,
        openai_api_key=os.getenv("LLM_API_KEY"),
        # callbacks=[StreamingStdOutCallbackHandler()],
        openai_api_base=os.getenv("LLM_API_BASE"),
    )


# 使用 @llm_tool 装饰器定义工具
@llm_tool
def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@llm_tool
def get_weather(city: str) -> str:
    """
    获取指定城市的天气信息
    
    Args:
        city: 城市名称
    
    Returns:
        天气信息
    """
    # 模拟天气数据
    weather_data = {
        "北京": "晴天，温度15°C",
        "上海": "多云，温度18°C",
        "深圳": "阴天，温度22°C",
    }
    return weather_data.get(city, f"{city}的天气信息暂未收录")


async def example_xml_tool_call_stream():
    """XML标签工具调用示例（异步流式版本）"""
    print("\n=== XML标签工具调用示例（异步流式） ===")

    # 初始化工具集成器
    tool_integration = LLMToolIntegration(tools=[get_current_time, get_weather])

    # 获取工具提示词
    tool_prompt = tool_integration.get_tool_prompt()

    # 初始化模型
    llm = init_llm()

    # 构建完整提示词
    query = "北京现在天气怎么样？现在几点了？"
    full_prompt = f"{tool_prompt}\n\n用户问题: {query}\n\n请根据需要调用工具来回答问题。"

    # 处理流式响应
    print("\n处理流式响应:")

    async for message in tool_integration.process_stream_response(llm.astream(full_prompt)):
        if isinstance(message, StreamMessage):
            print(message.content, end="", flush=True)
        elif isinstance(message, list):
            print("------工具调用结果-----")
            for result in message:
                print(f"工具: {result['tool_name']}")
                print(f"参数: {result['parameters']}")
                print(f"结果: {result['result']}")
                print("-" * 30)
            print("-----------")


if __name__ == "__main__":
    print("=" * 50)
    print("基于XML标签的工具调用示例（异步流式版本）")
    print("=" * 50)

    # 运行示例
    asyncio.run(example_xml_tool_call_stream())

    print("\n" + "=" * 50)
    print("所有示例运行完成!")
    print("=" * 50)
