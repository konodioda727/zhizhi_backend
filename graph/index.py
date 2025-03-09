from pydantic import BaseModel
from langgraph.graph import StateGraph, MessagesState
from langchain_core.messages import HumanMessage

class UserMessage(BaseModel):
    input: str

class CustomHumanMessage(HumanMessage):
    def __init__(self, content: str, author: str = 'system', **kwargs):
        super().__init__(content, **kwargs)
        self.author = author

def merge_additional_info(current, update):
    current.update(update)
    return current
# 创建状态图
def create_graph(fn):
    graph_builder = StateGraph(MessagesState)
    def get_content(state: MessagesState):
        messages = state["messages"]
        if not messages:  # 确保消息列表不为空
            return provide_approach(state)

        # 获取最后一条消息
        last_message = messages[-1]
        # 确保最后一条消息是 CustomHumanMessage 类型的实例
        if isinstance(last_message, CustomHumanMessage):
            last_message_content = last_message.content.lower()  # 获取最后一条消息内容并转换为小写
        else:
            last_message_content = last_message.get('content', '').lower()  # 默认为空字符串
        return last_message_content, messages
    
    def judge_need(state: MessagesState):
        last_message_content, messages = get_content(state)
        # 检查关键词或短语
        if "详细解释" in last_message_content or "不清楚" in last_message_content or "为什么" in last_message_content:
            return "provide_detailed_explanation"
        # 检查问题复杂性或其他条件
        elif "如何" in last_message_content and len(messages) > 1:  # 如果问题包含"如何"且不是第一次询问
            return "provide_detailed_explanation"
        # 默认不需要详细解释
        else:
            return "provide_approach"
        
    def provide_approach(state: MessagesState):
        # 提供问题解决思路
        last_content, messages = get_content(state)
        print(last_content)
        return {"messages": [CustomHumanMessage(content=f"存在如下问题：{last_content}，给出这个问题的简洁思路，引导思考，不给出答案")]}

    def provide_detailed_explanation(state: MessagesState):
        # 提供深入解释
        last_content, messages = get_content(state)
        return {"messages": [CustomHumanMessage(content=f"存在如下问题：{last_content}，关于这个问题的详细解释是...")]}
    def call_llm(state: MessagesState):
        # 提供深入解释
        last_content, messages = get_content(state)
        print(last_content)
        return {"messages": [CustomHumanMessage(content=fn(last_content))]}
    def end(state: MessagesState):
        # 结束
        last_content, messages = get_content(state)
        return {"messages": [CustomHumanMessage(content=last_content)]}
    def choose_direction(state: MessagesState):
        last_content, messages = get_content(state)
        return {"messages": [CustomHumanMessage(content=last_content)]}

    # 添加节点到图中
    graph_builder.add_node("judge_need", choose_direction)
    graph_builder.add_node("provide_approach", provide_approach)
    graph_builder.add_node("provide_detailed_explanation", provide_detailed_explanation)
    graph_builder.add_node("call_llm", call_llm)
    graph_builder.add_node("end", end)

    # 添加边
    graph_builder.add_edge("provide_approach", "call_llm")
    graph_builder.add_edge("provide_detailed_explanation", "call_llm")
    graph_builder.add_edge("call_llm", "end")
    graph_builder.add_conditional_edges("judge_need", judge_need)
    # 设置入口点
    graph_builder.set_entry_point("judge_need")

    # 编译图
    graph = graph_builder.compile()
    return graph

def execute_graph(graph, user_input: str):
    state = {"messages": [CustomHumanMessage(content=user_input, author='human')]}
    response = graph.invoke(state)
    return response["messages"][-1].content
