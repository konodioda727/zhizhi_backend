# 使用官方 Python 运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件到工作目录
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码到工作目录
COPY . .

# 暴露 FastAPI 默认的端口
EXPOSE 8000

# 运行 Uvicorn 服务器
CMD ["uvicorn", "main:app", "--host", "localhost", "--port", "8000"]
