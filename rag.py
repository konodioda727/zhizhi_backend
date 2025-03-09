from langchain_core.prompts import ChatPromptTemplate
import json

def extract_json(json_str):
    problem_data = json.loads(json_str)
    return problem_data

system_prompt = """
你是一个中文助手，叫做智知，根据以下context提供内容作答question的题目，尽量不直接给出答案，要引导用户思考，回答给出在answer中
Question: {question}
Context: {context}
History:
{history}
"""
system_ocr_prompt = ChatPromptTemplate.from_messages(
    [
        (
            """
            query中有一个问题，user_answer中为用户回答，只能按照```json\n \n```格式输出：  
            回答字段如下：
            1. answer: 对于query的详细回答
            2. correct: user_answer是否正确
            3. wrong_place: user_answer的错误位置
            4. wrong_place_length: user_answer的错误长度
            """
        ),
        ("human", "{query}"),
        ("human", "{user_answer}"),
    ]
)
import json

def parse_json_schema(json_str):
    try:
        # 去除字符串两端的```json和```，以及可能的前后空白字符
        json_str = json_str.strip()[7:-3].strip()  # 去除开始的```json和结束的```
        
        # 替换单引号为双引号
        corrected_json_str = json_str.replace("'", '"')
        print(corrected_json_str)
        # 解析JSON字符串
        json_obj = json.loads(corrected_json_str)
        return json_obj
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

# 定义用于构建历史记录的函数
def build_history(history):
    history_strings = [f"用户输入: {input}, 模型响应: {response}" for input, response in history]
    return "\n".join(history_strings)

# 更新创建RAG链的部分
def create_rag_chain_with_history(llm, retriever=None, system_prompt=system_prompt):
    def chain(input, history=[]):
        full_history = build_history(history)
        if(retriever != None):
            context = retriever.get_relevant_documents(input)
            context_text = "\n".join([doc.page_content for doc in context])
        else:
            context_text = ""
        prompt_with_history = system_prompt.format(question=input,context=context_text, history=full_history)
        
        response = llm(prompt_with_history)
        return response

    return chain
def create_ocr_rag_chain(llm, system_prompt=system_ocr_prompt):
    def chain(input, user_answer = "无"):
        chain = system_prompt | llm | parse_json_schema
        print(input,'user', user_answer)
        response = chain.invoke({"query": input, "user_answer": user_answer})
        result = {
            "input": input,
            "user_answer": user_answer,
            "response": response
        }
        return result
    return chain
# 构建RAG链
def create_rag(llm, retriever=None, system_prompt=system_prompt):
    return create_rag_chain_with_history(llm, retriever, system_prompt=system_prompt)
