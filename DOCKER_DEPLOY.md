# 🐳 Docker部署说明

## 🚀 快速开始

### 1. 单独部署NoneBot2
```bash
# 构建镜像
docker build -t qqbot .

# 运行容器
docker run -d --name qqbot \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/logs:/app/logs \
  qqbot
```

### 2. 使用Docker Compose（推荐）
```bash
# 启动所有服务
./start.sh

# 或手动执行
docker-compose up -d
```

## 📁 文件说明

- `Dockerfile` - Docker镜像构建文件
- `docker-compose.yml` - 多服务编排配置
- `.dockerignore` - Docker忽略文件列表
- `start.sh` - 快速启动脚本

## ⚙️ 配置说明

### NapCat连接配置
当前配置已连接到外部NapCat容器 `lama`：

- `docker-compose.yml` 中使用 `external_links` 连接到 `lama` 容器
- `config.py` 中WebSocket地址为 `ws://napcat:3001` (容器内部网络)

如果NapCat容器名不是 `lama`，请修改 `docker-compose.yml` 中的：
```yaml
external_links:
  - 你的容器名:napcat
```

如果NapCat不在Docker中，请修改 `config.py` 中的 `onebot_ws_urls`：
```python
onebot_ws_urls: List[str] = ["ws://你的NapCat服务器IP:3001"]
```

### 环境变量
可以在 `docker-compose.yml` 中添加环境变量：
```yaml
environment:
  - NAPCAT_HOST=your-napcat-server-ip
```

## 📊 管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f qqbot

# 重启服务
docker-compose restart qqbot

# 停止服务
docker-compose down

# 更新代码后重新构建
docker-compose build --no-cache
docker-compose up -d
```

## 🔧 故障排除

### 连接问题
```bash
# 检查NapCat容器状态
docker-compose ps napcat

# 检查网络连接
docker-compose exec qqbot ping napcat

# 查看详细日志
docker-compose logs qqbot
```

### 权限问题
确保宿主机用户有Docker权限，或使用 `sudo` 运行Docker命令。

### 端口冲突
如果3001端口被占用，修改 `docker-compose.yml` 中的端口映射。
