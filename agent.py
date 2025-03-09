from typing import Annotated, Sequence, TypedDict, List
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
import json

# 定义状态类型
class AnalysisState(TypedDict):
    question: str 
    llm: any
    code_solution: str 
    nodes: list 
    execution: dict 
    explaination: str
    messages: Sequence[BaseMessage]
    current_step: str

# 定义输出模型
class CodeSolution(BaseModel):
    """solution to the question"""
    explaination: str = Field(description="题目的解决思路讲解")
    code: str = Field(description="完整的题解代码")
        

class CodeNode(BaseModel):
    """node of the code"""
    explaination: str = Field(description="该步做了什么事情")
    nodeType: int = Field(description="节点类型(1:正常节点,2:控制节点,3:循环节点)")
    nodeName: str = Field(description="节点名称")
    nextNode: List[str] = Field(description="所有直接子节点名称, 子节点必须出现在nodes数组中")

    class Config:
        extra = 'allow'
        title = 'CodeNode'

class ExecutionStep(BaseModel):
    """execution step of the code"""
    explaination: str = Field(description="该步做了什么事情")
    variables: dict = Field(description="该步执行完的变量值")
    nodeName: str = Field(description="节点名称,节点必须存在于nodes数组中")
    nextNode: List[str] = Field(description="所有直接子节点名称")

    class Config:
        extra = 'allow'
        title = 'ExecutionStep'

class NodeList(BaseModel):
    """node list"""
    nodes: List[CodeNode] = Field(description="节点列表")

class ExecutionList(BaseModel):
    """execution list"""
    steps: List[ExecutionStep] = Field(description="执行步骤列表")

# 创建解析器
code_parser = PydanticOutputParser(pydantic_object=CodeSolution)
nodes_parser = PydanticOutputParser(pydantic_object=List[CodeNode])
execution_parser = PydanticOutputParser(pydantic_object=List[ExecutionStep])

# 更新提示词
anal_prompt = """你是一个代码分析专家，请分析题目并给出解决方案代码。

请严格按照以下 JSON 格式输出，不要包含任何其他内容：
{
    "explaination": "请详细解释解题思路，包括算法选择的原因和实现要点",
    "code": "请提供完整的、可运行的代码，包含必要的注释"
}

注意：
1. explaination 必须详细说明解题思路
2. code 必须是完整的、可运行的代码
3. 请确保 JSON 格式完全正确
"""

generate_nodes_prompt = """请将代码逻辑拆分为节点，每个节点展示实时值。

请严格按照以下 JSON 格式输出，不要包含任何其他内容：
{
    "nodes": [
        {
            "explaination": "详细说明该节点的功能和作用",
            "nodeType": 1,
            "nodeName": "节点的唯一标识名称",
            "nextNode": ["下一个节点的名称列表"]
        }
    ]
}

注意：
1. nodeType 必须是以下值之一：
   - 1: 正常节点（普通操作）
   - 2: 控制节点（if/else等条件判断）
   - 3: 循环节点（for/while等循环）
2. nodeName 必须唯一
3. nextNode 必须是一个数组，包含所有可能的下一个节点名称
4. 所有节点必须形成一个完整的执行流程
5. 请确保 JSON 格式完全正确
"""

execute_example_prompt = """根据上述节点,请给出示例并执行，展示每步变量值和行为解释。

请严格按照以下 JSON 格式输出，确保包含所有必需字段：
{
    "steps": [
        {
            "explaination": "该步做了什么事情",
            "variables": {
                "变量1": "值1",
                "变量2": "值2"
                // 如果没有变量变化，至少返回空对象 {}
            },
            "nodeName": "当前节点名称",
            "nextNode": "下一个节点名称"
        }
    ]
}

注意：
1. variables 字段必须存在，如果该步骤没有变量变化，请返回空对象 {}
2. 每个步骤都必须包含 explaination、variables、nodeName 和 nextNode 这四个字段
3. 请确保 JSON 格式完全正确
"""

class CodeAnalysisAgent:
    @staticmethod
    def analyze_question(state: AnalysisState) -> AnalysisState:
        messages = [
            SystemMessage(content="你是一个代码分析专家。请按照指定格式输出。"),
            HumanMessage(content=anal_prompt + "\n题目：" + state["question"])
        ]
        response = state["llm"].with_structured_output(CodeSolution).invoke(messages)
        state["code_solution"] = response.code
        state["explaination"] = response.explaination
       
        state["current_step"] = "generate_nodes"
        return state

    @staticmethod
    def generate_nodes(state: AnalysisState) -> AnalysisState:
        messages = [
            SystemMessage(content="请按照指定格式输出节点信息。"),
            HumanMessage(content=generate_nodes_prompt + "\n代码：" + str(state["code_solution"]))
        ]
        response = state["llm"].with_structured_output(NodeList).invoke(messages)      
        state["nodes"] = [node.dict() for node in response.nodes]
        state["current_step"] = "execute_example"
        return state

    @staticmethod
    def execute_example(state: AnalysisState) -> AnalysisState:
        messages = [
            SystemMessage(content="请按照指定格式输出执行步骤。"),
            HumanMessage(content=execute_example_prompt + "\n节点：" + str(state["nodes"]))
        ]
        response = state["llm"].with_structured_output(ExecutionList).invoke(messages)
        
        state["execution"] = [step.dict() for step in response.steps]
        state["current_step"] = "end"
        return state

    # 构建工作流图
    @staticmethod
    def create_analysis_graph():
        workflow = StateGraph(AnalysisState)
        
        # 添加节点
        workflow.add_node("analyze_question", CodeAnalysisAgent.analyze_question)
        workflow.add_node("generate_nodes", CodeAnalysisAgent.generate_nodes)
        workflow.add_node("execute_example", CodeAnalysisAgent.execute_example)
        
        # 设置边和条件
        workflow.add_edge("analyze_question", "generate_nodes")
        workflow.add_edge("generate_nodes", "execute_example")
        
        # 设置入口点和结束条件
        workflow.set_entry_point("analyze_question")
        
        return workflow.compile()

    # 修改原有的 invoke_question 函数
    def invoke_question(self, llm, question, max_retries=3, retry_delay=10):
        graph = self.create_analysis_graph()
        
        # 初始化状态
        initial_state = AnalysisState(
            question=question,
            code_solution="",
            nodes=[],
            llm=llm,
            execution={},
            messages=[],
            current_step="analyze_question"
        )
        
        # 执行工作流
        final_state = graph.invoke(initial_state)
        
        # 移除 llm 字段后返回
        final_state_dict = final_state.copy()
        final_state_dict.pop('llm', None)
        return final_state_dict