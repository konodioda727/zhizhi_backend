from model import llm, openai
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
import json
import time
from typing import Optional
import re
from fastapi.middleware.cors import CORSMiddleware
from agent import CodeAnalysisAgent as Agent

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的源
    allow_credentials=True,  # 允许发送Cookie
    allow_methods=["*"],  # 允许的方法，如GET、POST等，使用["*"]来允许所有方法
    allow_headers=["*"],  # 允许的请求头，使用["*"]来允许所有请求头
)

class CodeAnalysisRequest(BaseModel):
    code: str
    model_type: Optional[str] = "openai"  # 默认使用openai模型

system_prompt = """
代码：{code}

按一下步骤完成任务：
1. 简化逻辑，得到精简后伪代码, 并用例子辅助理解
2. 将上一步生成的逻辑拆分为一个个节点, 每一个节点需要展示当前例子的实时值,并用 json 格式输出
3. 给出一个实例，并**从头到尾执行示例**，给出每步变量的值，并解释该步的行为

**必须只输出json**，json 内容分为： explaination 和 struct  两部分
- explaination 部分: 为代码逻辑讲解
- sturct 部分:
- - variables: 例子变量集合, 每一步执行完变量的值
- - explaination: 该步做了什么事情，用中文回答
- - nodeType: 节点类型, 1 代表正常节点, 2 代表控制节点, 3 代表循环节点
- - nodeName: 节点名称
- - nextNode: 下一个节点名称
"""

def invoke(llm, code, max_retries=3, retry_delay=10):
    prompt = system_prompt.format(code=code)
    retries = 0
    while retries < max_retries:
        try:
            result = llm(prompt)
            return result
        except Exception as e:
            if "429" in str(e):
                print(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retries += 1
                retry_delay *= 2  # Exponential backoff
            else:
                raise e
    raise Exception("Max retries exceeded. Failed to get a response.")

# 添加新的API端点
@app.post("/question")
def anallyze_question( 
    question: str = Form(None),
    model_type: str = Form(default="openai"),
):
    try:
        # 选择模型
        model = openai if model_type == "openai" else llm
        print("\n\n=====question=====\n\n", question)
        if question == None: 
            raise HTTPException(status_code=400, detail=str("question不能为空"))
        agent = Agent()
        # 调用模型进行分析
        result = agent.invoke_question(llm=model, question=question)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 添加新的API端点
@app.post("/analyze")
async def analyze_code(
    code: str = Form(None),
    model_type: str = Form(default="openai"),
):
    try:
        
        # 选择模型
        model = openai if model_type == "openai" else llm
        print("\n\n=====code=====\n\n",code)
        # 调用模型进行分析
        result = invoke(model, code)
        json_pattern = r'```json([\s\S]*?)```'
        match = re.search(json_pattern, result.content, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                json_obj = json.loads(json_str)
                return {"status": "success", "result": json_obj}
            except json.JSONDecodeError:
                return {"status": "error", "result": "Invalid JSON format"}
        else:
            return {"status": "error", "result": "No JSON content found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    # dataset_path = "leetcode_dataset"
    # if os.path.exists(dataset_path):
    #     ds = load_from_disk(dataset_path)
    # else:
    #     ds = load_dataset("greengerong/leetcode", split="train")
    #     ds.save_to_disk(dataset_path)
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    agent = Agent()
    print(agent.invoke_question(llm=openai, question="鸡有8只,兔子有4只,一共多少条腿"))