from langchain_community.llms.moonshot import Moonshot
import os

os.environ["MOONSHOT_API_KEY"] = "sk-NoXsbhonxcroaTvbzOPPqDOIkqsp9FervmPE5rCGkbwR2H6V"
os.environ["QIANFAN_AK"] = "GFPPuWQ2XgPyB6o3FsUqmUSU"
os.environ["QIANFAN_SK"] = "nXhmp2CjXIhU5fxTTGT0fGx6nYyHuFY8"

llm = Moonshot(model="moonshot-v1-128k")