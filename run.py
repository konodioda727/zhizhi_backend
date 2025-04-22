import uvicorn
from main import app
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    """
    应用程序启动入口
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,  # 开发模式下启用热重载
        workers=1,    # 工作进程数
        log_level="info",
        proxy_headers=True,  # 启用代理头支持
        forwarded_allow_ips="*",  # 允许的转发IP
    )

if __name__ == "__main__":
    print("正在启动智之管理系统后端服务...")
    print("API文档地址: http://localhost:8000/api/docs")
    main()