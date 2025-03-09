import requests
import json
import base64
import urllib.parse as urlparse

with open('zhizhi_secrete.json') as json_file:
    data = json.load(json_file)
    client_id, client_secret, base_url = data['baidu_client_id'], data['baidu_client_secret'], data['baidu_base_url']

def get_access_token(client_id, client_secret):
    url = f"{base_url}/oauth/2.0/token?grant_type=client_credentials"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get('access_token')

def get_image_content_as_base64(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode("utf8")
    else:
        return None

def gene_resp(access_token, image_base64):
    url = f"{base_url}/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
    
    payload = {
        'image': image_base64,
        'detect_direction': 'false',
        'detect_language': 'false',
        'paragraph': 'false',
        'probability': 'false'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    words_rephrased = [item["words"] for item in response.json().get("words_result", [])]
    result = "\n".join(words_rephrased)
    return result
def read_image(img_base64=""):
    access_token = get_access_token(client_id, client_secret)
    if img_base64:
        return gene_resp(access_token, img_base64)
    else:
        return "Failed to retrieve image."
def read_image_from_url(image_url="https://s2.loli.net/2024/09/04/CFlIpU49jMVzqfo.png"):
    img_base64 = get_image_content_as_base64(image_url)
    read_image(img_base64)
    
def read_question_answer_pair(image_base64=get_image_content_as_base64('https://s2.loli.net/2024/09/08/73a2sJchuVzgbTC.png')):
    access_token = get_access_token(client_id, client_secret)
    url = f"{base_url}/rest/2.0/ocr/v1/doc_analysis?access_token={access_token}"
    
    payload = {
        'image': image_base64,
        'detect_direction': 'false',
        'detect_language': 'false',
        'paragraph': 'true',  # 设置为true以便将文本段落分组
        'probability': 'false'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    results = response.json().get("results", [])
    
    # 初始化结果数组
    output_results = []
    
    # 用于暂存问题和手写回答的变量
    current_question = ""
    current_answer = ""
    for item in results:
        word = item["words"]["word"]
        words_type = item["words_type"]

        if words_type == "print":
            if not current_answer:  # 如果当前问题不为空，则保存上一个问题和答案
                current_question += word
            else:
                output_results.append({"question": current_question, "answer": current_answer})
                current_question = word  # 重置问题
                current_answer = ""
        elif words_type == "handwriting":
            current_answer += word + " " 
    # 检查是否有最后一个问题和答案未被添加
    if current_question or current_answer:
        output_results.append({"question": current_question.strip(), "user_answer": current_answer.strip()})
    # print(str(output_results))
    return output_results
if __name__ == '__main__':
    print(read_question_answer_pair())