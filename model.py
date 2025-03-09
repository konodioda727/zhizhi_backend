from langchain_community.llms.moonshot import Moonshot
from langchain_openai import ChatOpenAI
import os

os.environ["MOONSHOT_API_KEY"] = "sk-NoXsbhonxcroaTvbzOPPqDOIkqsp9FervmPE5rCGkbwR2H6V"
os.environ["QIANFAN_AK"] = "GFPPuWQ2XgPyB6o3FsUqmUSU"
os.environ["QIANFAN_SK"] = "nXhmp2CjXIhU5fxTTGT0fGx6nYyHuFY8"

llm = Moonshot(model="moonshot-v1-128k")
openai = ChatOpenAI(base_url="https://api.chatanywhere.tech/v1", model="gpt-4o", api_key="sk-B8btNeZCQ99ZvkGBNDK8iIr3qV0azJauWArMdnCh1MLIYqJX")
vision_llm = Moonshot(model="moonshot-v1-8k-vision-preview")