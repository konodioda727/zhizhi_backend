import os
import base64
import requests  # 添加 requests 导入
from openai import OpenAI

os.environ["MOONSHOT_API_KEY"] = "sk-NoXsbhonxcroaTvbzOPPqDOIkqsp9FervmPE5rCGkbwR2H6V"

client = OpenAI(
    api_key=os.environ.get("MOONSHOT_API_KEY"),
    base_url="https://api.moonshot.cn/v1",
)

# 图片 URL
image_path = "images/geo2.png"

# 如果是 URL，则下载图片
if image_path.startswith(('http://', 'https://')):
    try:
        response = requests.get(image_path)
        response.raise_for_status()  # 检查请求是否成功
        image_data = response.content
        # 从 URL 获取文件扩展名
        file_extension = os.path.splitext(image_path)[1].lstrip('.')
        if not file_extension:
            # 如果 URL 中没有扩展名，从 content-type 获取
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                file_extension = 'jpeg'
            elif 'png' in content_type:
                file_extension = 'png'
            else:
                file_extension = 'jpeg'  # 默认使用 jpeg
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download image: {str(e)}")
else:
    # 如果是本地文件路径，直接读取
    with open(image_path, "rb") as f:
        image_data = f.read()
        file_extension = os.path.splitext(image_path)[1].lstrip('.')

# 构建 base64 图片 URL
image_url = f"data:image/{file_extension};base64,{base64.b64encode(image_data).decode('utf-8')}"

completion = client.chat.completions.create(
    model="moonshot-v1-8k-vision-preview",
    messages=[
        {"role": "system", "content": "你是智知, 一个教学助手, 请详细回答用户提出的问题。解答需要包含以下步骤：\n1. 分析问题类型，理解题意。\n2. 给出详细的解答过程，步骤要清晰。\n3. 使用 LaTeX 编写证明过程。\n4. 在解答完毕后，进行自我检查，确认解题过程没有疏漏，并对可能的错误进行更正。"},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",  # <-- 使用 image_url 类型来上传图片，内容为使用 base64 编码过的图片内容
                    "image_url": {
                        "url": image_url,
                    },
                },
                {
                    "type": "text",
                    "text": "请解答图中的几何问题,并详细展示推理和证明过程，使用LaTeX书写。",
                },
            ],
        },
    ],
)


print(completion.choices[0].message.content)