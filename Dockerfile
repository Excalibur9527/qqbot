# 使用Python 3.9作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制项目文件
COPY . .

# 创建日志和数据目录
RUN mkdir -p logs data

# 暴露端口（如果需要的话）
# EXPOSE 8080

# 启动命令
CMD ["python", "bot.py"]
