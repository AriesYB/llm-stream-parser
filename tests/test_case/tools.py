"""
LLM工具模块
提供工具注解、提示词生成和工具集成功能
"""

import asyncio
import functools
import inspect
import re
import xml.etree.ElementTree as ET
from typing import Callable, List, Union, Optional, Dict, Any, AsyncGenerator, AsyncIterator

import llm_stream_parser
from llm_stream_parser import StreamParser, StreamMessage

# 全局工具注册表
_llm_tools_registry: Dict[str, Callable] = {}
_llm_tools_metadata: Dict[str, Dict[str, Any]] = {}


def llm_tool(func_or_name: Union[Callable, str, None] = None,
             name: Optional[str] = None,
             description: Optional[str] = None):
    """
    自定义工具装饰器，用于注册LLM可调用的工具

    :param func_or_name: 函数对象或工具名称
    :param name: 工具名称，默认使用函数名
    :param description: 工具描述，默认使用函数文档字符串
    """

    def decorator(func: Callable) -> Callable:
        # 确定工具名称
        nonlocal name, description
        tool_name = name or getattr(func_or_name, '__name__', None) or func.__name__

        # 如果 func_or_name 是字符串且没有提供 name，使用该字符串作为工具名
        if isinstance(func_or_name, str) and name is None:
            tool_name = func_or_name

        # 确定工具描述 - 优先使用传入的description，否则使用函数文档字符串
        if description is None:
            tool_description = func.__doc__ or ""
            # 清理文档字符串格式
            if tool_description:
                tool_description = tool_description.strip()
        else:
            tool_description = description

        # 获取函数签名信息
        sig = inspect.signature(func)
        parameters = {}
        for param_name, param in sig.parameters.items():
            parameters[param_name] = {
                'name': param_name,
                'type': param.annotation if param.annotation != param.empty else Any,
                'default': param.default if param.default != param.empty else None,
                'has_default': param.default != param.empty
            }

        # 注册工具
        _llm_tools_registry[tool_name.lower()] = func
        _llm_tools_metadata[tool_name.lower()] = {
            "name": tool_name,
            "description": tool_description,
            "func": func,
            "signature": str(sig),
            "parameters": parameters,
            "return_type": sig.return_annotation if sig.return_annotation != sig.empty else Any
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 添加额外属性便于访问
        wrapper.name = tool_name
        wrapper.description = tool_description
        wrapper.is_llm_tool = True
        wrapper.signature = str(sig)
        wrapper.parameters = parameters

        # 添加invoke方法，支持通过字典传参
        def invoke(params: Union[Dict[str, Any], List[Any], Any] = None):
            # 处理无参数情况
            if params is None:
                params = {}

            # 检查是否为绑定方法
            is_bound_method = hasattr(func, '__self__') and func.__self__ is not None

            # 如果是关键字参数形式
            if isinstance(params, dict):
                if is_bound_method:
                    return func(**params)
                else:
                    return func(**params)
            # 如果是位置参数形式
            elif isinstance(params, (list, tuple)):
                if is_bound_method:
                    return func(*params)
                else:
                    return func(*params)
            # 如果是单个值
            else:
                if is_bound_method:
                    return func(params)
                else:
                    return func(params)

        wrapper.invoke = invoke

        return wrapper

    # 处理 @llm_tool 和 @llm_tool(...) 两种情况
    if callable(func_or_name):
        # 直接使用 @llm_tool 的情况
        return decorator(func_or_name)
    else:
        # 使用 @llm_tool(...) 的情况
        return decorator


def get_tool(tool_name: str) -> Callable:
    """根据工具名称获取工具函数"""
    return _llm_tools_registry.get(tool_name.lower())


def get_tool_metadata(tool_name: str) -> Dict[str, Any]:
    """获取工具的元数据信息"""
    return _llm_tools_metadata.get(tool_name.lower(), {})


def list_tools() -> List[str]:
    """列出所有已注册的工具名称"""
    return list(_llm_tools_registry.keys())


def get_all_tools_metadata() -> Dict[str, Dict[str, Any]]:
    """获取所有工具的完整元数据"""
    return _llm_tools_metadata.copy()


def generate_tool_prompt(tools: Optional[List[str]] = None) -> str:
    """
    生成工具调用的XML提示词

    Args:
        tools: 指定要包含的工具名称列表，如果为None则包含所有已注册的工具

    Returns:
        格式化的XML工具提示词字符串
    """
    all_metadata = get_all_tools_metadata()

    # 如果指定了工具列表，只包含指定的工具
    if tools is not None:
        filtered_metadata = {}
        for tool_name in tools:
            if tool_name.lower() in all_metadata:
                filtered_metadata[tool_name.lower()] = all_metadata[tool_name.lower()]
        metadata_to_use = filtered_metadata
    else:
        metadata_to_use = all_metadata

    if not metadata_to_use:
        return ""

    prompt_parts = [
        "你可以使用以下工具来帮助完成任务。使用XML格式调用工具：",
        "",
        "工具调用格式：",
        "<tools>",
        "   <tool_name1>",
        "       <parameter_name1>参数值1</parameter_name1>",
        "       <parameter_name2>参数值2</parameter_name2>",
        "   </tool_name1>",
        "   <tool_name2>",
        "       <parameter_name3>参数值3</parameter_name3>",
        "       <parameter_name4>参数值4</parameter_name4>",
        "   </tool_name2>",
        "</tools>",
        "没有参数时写<tool_name></tool_name>不要简化为<tool_name/>",
        "可用工具列表："
    ]

    for tool_name, metadata in metadata_to_use.items():
        prompt_parts.append(f"\n{metadata['name']}:")
        prompt_parts.append(f"描述: {metadata['description']}")

        parameters = metadata['parameters']
        if parameters:
            prompt_parts.append("参数:")
            for param_name, param_info in parameters.items():
                param_type = param_info['type'].__name__ if hasattr(param_info['type'], '__name__') else str(
                    param_info['type'])
                if param_info['has_default']:
                    prompt_parts.append(
                        f"  - {param_name} ({param_type}, 可选, 默认值: {param_info['default']}): 参数描述")
                else:
                    prompt_parts.append(f"  - {param_name} ({param_type}, 必需): 参数描述")
        else:
            prompt_parts.append("参数: 无")

    prompt_parts.extend([
        "",
        "注意事项:",
        "1. 使用工具时，请确保提供所有必需的参数",
        "2. 参数值应该放在XML标签之间",
        "3. 允许调用多个工具",
    ])

    return "\n".join(prompt_parts)


def execute_tool_calls(text: str = "", tool_calls: List[Dict[str, Any]] = [],
                       tool_set: Optional[set[str]] = None) -> List[Dict[str, Any]]:
    """
    解析并执行工具调用

    Args:
        text: 包含工具调用的文本
        tool_calls: 已解析的工具名和参数
        tool_set: 指定工具范围

    Returns:
        执行结果列表
    """
    if text and text != "":
        tool_calls = extract_tool_calls(text)
    else:
        if not tool_calls or tool_calls == []:
            return []
    results = []

    for tool_call in tool_calls:
        tool_name = tool_call['tool_name']
        parameters = tool_call['parameters']

        if tool_set and tool_name not in tool_set:
            continue

        try:
            # 获取工具元数据以检查参数类型
            metadata = get_tool_metadata(tool_name)
            if not metadata:
                result = f"错误: 工具 '{tool_name}' 未找到"
            else:
                # 转换参数类型
                converted_params = _convert_parameter_types(parameters, metadata['parameters'])

                # 获取工具函数
                tool_func = get_tool(tool_name)
                if tool_func is None:
                    result = f"错误: 无法获取工具 '{tool_name}'"
                else:
                    # 检查是否是绑定方法（有self参数）
                    if hasattr(tool_func, '__self__'):
                        # 对于绑定方法，直接调用
                        tool_result = tool_func(**converted_params)
                    else:
                        # 对于普通函数，使用invoke_tool
                        tool_result = tool_func(**converted_params)
                    result = tool_result
        except Exception as e:
            result = f"执行工具 '{tool_name}' 时出错: {str(e)}"

        results.append({
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result
        })

    return results


async def aexecute_tool_calls(text: str = "", tool_calls: List[Dict[str, Any]] = [],
                              tool_set: Optional[set[str]] = None) -> List[Dict[str, Any]]:
    """
    异步解析并执行工具调用

    Args:
        text: 包含工具调用的文本
        tool_calls: 已解析的工具名和参数
        tool_set: 指定工具范围

    Returns:
        执行结果列表
    """
    if text and text != "":
        tool_calls = extract_tool_calls(text)
    else:
        if not tool_calls or tool_calls == []:
            return []
    results = []

    for tool_call in tool_calls:
        tool_name = tool_call['tool_name']
        parameters = tool_call['parameters']

        if tool_set and tool_name not in tool_set:
            continue

        try:
            # 获取工具元数据以检查参数类型
            metadata = get_tool_metadata(tool_name)
            if not metadata:
                result = f"错误: 工具 '{tool_name}' 未找到"
            else:
                # 转换参数类型
                converted_params = _convert_parameter_types(parameters, metadata['parameters'])

                # 获取工具函数
                tool_func = get_tool(tool_name)
                if tool_func is None:
                    result = f"错误: 无法获取工具 '{tool_name}'"
                else:
                    # 检查是否是绑定方法（有self参数）
                    if hasattr(tool_func, '__self__'):
                        # 对于绑定方法，直接调用
                        tool_result = tool_func(**converted_params)
                    else:
                        # 对于普通函数，使用invoke_tool
                        tool_result = tool_func(**converted_params)
                    result = tool_result
        except Exception as e:
            result = f"执行工具 '{tool_name}' 时出错: {str(e)}"

        results.append({
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result
        })

    return results


def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取所有工具调用

    Args:
        text: 包含工具调用的文本

    Returns:
        工具调用列表
    """
    tool_calls = []
    tool_call_pattern = re.compile(r'<([^/][^>]*)>(.*?)</\1>', re.DOTALL)

    for match in tool_call_pattern.finditer(text):
        tool_name = match.group(1).strip()
        content = match.group(2).strip()

        # 尝试解析参数
        try:
            params = _extract_parameters(content)
            tool_calls.append({
                'tool_name': tool_name,
                'parameters': params
            })
        except Exception as e:
            # 如果解析失败，记录错误但继续处理其他工具调用
            print(f"解析工具调用 {tool_name} 失败: {str(e)}")
            continue

    return tool_calls


def _extract_parameters(content: str) -> Dict[str, Any]:
    """
    从工具调用内容中提取参数

    Args:
        content: 工具调用内容

    Returns:
        参数字典
    """
    params = {}

    # 尝试使用XML解析参数
    try:
        # 包装内容以确保XML格式正确
        wrapped_content = f"<root>{content}</root>"
        root = ET.fromstring(wrapped_content)

        for child in root:
            # 处理嵌套的XML标签
            if len(child) > 0:
                # 如果有子标签，递归解析
                params[child.tag] = _xml_element_to_dict(child)
            else:
                # 如果是叶子节点，获取文本内容
                params[child.tag] = child.text or ""
    except ET.ParseError:
        # 如果XML解析失败，尝试使用正则表达式
        param_pattern = re.compile(r'<([^>]+)>(.*?)</\1>', re.DOTALL)
        for match in param_pattern.finditer(content):
            param_name = match.group(1).strip()
            param_value = match.group(2).strip()
            params[param_name] = param_value

    return params


def _xml_element_to_dict(element: ET.Element) -> Any:
    """
    将XML元素转换为字典或值

    Args:
        element: XML元素

    Returns:
        转换后的字典或值
    """
    result = {}

    # 如果有属性，添加到结果中
    if element.attrib:
        result['@attributes'] = element.attrib

    # 如果有子元素
    if len(element) > 0:
        for child in element:
            child_data = _xml_element_to_dict(child)
            if child.tag in result:
                # 如果标签已存在，转换为列表
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
    else:
        # 如果是叶子节点，返回文本内容
        return element.text or ""

    return result


def _convert_parameter_types(params: Dict[str, Any], param_metadata: Dict[str, Dict]) -> Dict[str, Any]:
    """
    转换参数类型以匹配工具函数签名

    Args:
        params: 原始参数字典
        param_metadata: 参数元数据

    Returns:
        转换后的参数字典
    """
    converted_params = {}

    for param_name, param_value in params.items():
        if param_name in param_metadata:
            param_type = param_metadata[param_name]['type']
            try:
                # 尝试转换参数类型
                if param_type == int:
                    converted_params[param_name] = int(float(param_value)) if '.' in param_value else int(
                        param_value)
                elif param_type == float:
                    converted_params[param_name] = float(param_value)
                elif param_type == bool:
                    converted_params[param_name] = param_value.lower() in ('true', '1', 'yes', 'on')
                elif param_type == str:
                    converted_params[param_name] = str(param_value)
                else:
                    # 对于其他类型，保持原样
                    converted_params[param_name] = param_value
            except (ValueError, TypeError):
                # 如果转换失败，保持原样并让工具函数处理
                converted_params[param_name] = param_value
        else:
            # 如果参数不在元数据中，保持原样
            converted_params[param_name] = param_value

    return converted_params


class LLMToolIntegration:
    """
    LLM工具集成类
    提供完整的工具调用解决方案，包括提示词生成和结果解析
    """

    def __init__(self, tools: List = []):
        """
        初始化集成器

        Args:
            tools: 要使用的工具列表，如果为None则使用所有已注册的工具
        """
        self.tools = [tool.name.lower() for tool in tools]
        self.tool_prompt = generate_tool_prompt(self.tools)

    def get_tool_prompt(self) -> str:
        """
        获取工具提示词

        Returns:
            格式化的工具提示词
        """
        return self.tool_prompt

    async def process_stream_response(self, response_stream: AsyncIterator) -> AsyncGenerator:
        """
        处理流式响应，解析工具调用并返回流式结果

        Args:
            response_stream: 大模型的流式响应

        Yields:
            解析后的流式消息或工具执行结果
        """
        stream_parser = StreamParser(tags={"think": "思考中", "tools": "工具调用"}, enable_tags_streaming=True)
        tools_result = []

        async def handle_message(message: StreamMessage) -> Optional[StreamMessage]:
            """统一处理解析后的消息：屏蔽工具调用流式输出，完整工具调用直接执行。"""
            if message.step_name != "工具调用":
                return message

            if message.is_complete:
                tools_result.extend(await aexecute_tool_calls(text=message.content, tool_set=set(self.tools)))

            return None

        async for chunk in response_stream:
            messages = stream_parser.parse_chunk(chunk.content)
            for message in messages:
                handled_message = await handle_message(message)
                if handled_message is not None:
                    yield handled_message

        final_message = stream_parser.finalize()
        if final_message:
            handled_message = await handle_message(final_message)
            if handled_message is not None:
                yield handled_message

        if tools_result:
            yield tools_result

    def add_tool(self, tool_func, name: Optional[str] = None, description: Optional[str] = None):
        """
        动态添加工具

        Args:
            tool_func: 工具函数
            name: 工具名称
            description: 工具描述
        """
        # 使用装饰器注册工具
        if name or description:
            decorated_tool = llm_tool(name=name, description=description)(tool_func)
        else:
            decorated_tool = llm_tool(tool_func)

        # 更新提示词
        self.tools.append(decorated_tool.name.lower())
        self.tool_prompt = generate_tool_prompt(self.tools)

        return decorated_tool

    def get_available_tools(self) -> List[str]:
        """
        获取可用工具列表

        Returns:
            工具名称列表
        """
        if self.tools:
            return self.tools
        return list_tools()

    def get_tool_metadata(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具元数据

        Args:
            tool_name: 工具名称

        Returns:
            工具元数据字典
        """
        return get_tool_metadata(tool_name)
