#!/bin/bash

# QQ机器人Docker部署脚本

echo "🐳 构建并启动QQ机器人..."

# 构建Docker镜像
echo "📦 构建Docker镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

echo "✅ 部署完成！"
echo ""
echo "📊 查看状态:"
echo "  docker-compose ps"
echo ""
echo "📝 查看日志:"
echo "  docker-compose logs -f qqbot"
echo ""
echo "🛑 停止服务:"
echo "  docker-compose down"
