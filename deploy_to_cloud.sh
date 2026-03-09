#!/bin/bash

# ETHUSDT 量化系统 - 云服务器部署脚本
# 适用于腾讯云轻量应用服务器（Ubuntu 20.04+）

set -e

echo "=========================================="
echo "ETHUSDT 量化系统 - 云服务器部署"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 检查系统
echo -e "${YELLOW}[1/8] 检查系统环境...${NC}"
if [ "$(id -u)" != "0" ]; then
   echo -e "${RED}错误: 此脚本需要 root 权限${NC}"
   exit 1
fi

# 2. 安装 Docker
echo -e "${YELLOW}[2/8] 安装 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✓ Docker 安装完成${NC}"
else
    echo -e "${GREEN}✓ Docker 已安装${NC}"
fi

# 3. 安装 Docker Compose
echo -e "${YELLOW}[3/8] 安装 Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose 安装完成${NC}"
else
    echo -e "${GREEN}✓ Docker Compose 已安装${NC}"
fi

# 4. 创建项目目录
echo -e "${YELLOW}[4/8] 创建项目目录...${NC}"
PROJECT_DIR="/opt/ethusdt-trading"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR
mkdir -p data logs
echo -e "${GREEN}✓ 项目目录创建完成: $PROJECT_DIR${NC}"

# 5. 创建 docker-compose.yml
echo -e "${YELLOW}[5/8] 创建 Docker Compose 配置...${NC}"
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  ethusdt-trading:
    image: python:3.9-slim
    container_name: ethusdt-quantitative-system
    working_dir: /app
    ports:
      - "8501:8501"
    environment:
      - TZ=Asia/Shanghai
      - COINEX_ACCESS_ID=${COINEX_ACCESS_ID}
      - COINEX_SECRET_KEY=${COINEX_SECRET_KEY}
    volumes:
      - ./:/app
      - ./data:/app/data
      - ./logs:/app/logs
    command: >
      bash -c "
        apt-get update && apt-get install -y gcc g++ curl &&
        pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple &&
        streamlit run app_coinex.py --server.headless=true --server.port=8501 --server.address=0.0.0.0
      "
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
EOF
echo -e "${GREEN}✓ Docker Compose 配置创建完成${NC}"

# 6. 配置防火墙
echo -e "${YELLOW}[6/8] 配置防火墙...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 8501/tcp
    ufw reload
    echo -e "${GREEN}✓ UFW 防火墙规则添加完成（端口 8501）${NC}"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8501/tcp
    firewall-cmd --reload
    echo -e "${GREEN}✓ Firewalld 防火墙规则添加完成（端口 8501）${NC}"
else
    echo -e "${YELLOW}⚠ 未检测到防火墙，请手动配置安全组开放端口 8501${NC}"
fi

# 7. 创建环境变量文件
echo -e "${YELLOW}[7/8] 配置环境变量...${NC}"
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# CoinEx API 配置（请修改为您的实际密钥）
COINEX_ACCESS_ID=your_access_id_here
COINEX_SECRET_KEY=your_secret_key_here

# 时区设置
TZ=Asia/Shanghai
EOF
    echo -e "${YELLOW}⚠ 请编辑 .env 文件配置您的 API Key${NC}"
    echo -e "${YELLOW}  命令: nano /opt/ethusdt-trading/.env${NC}"
else
    echo -e "${GREEN}✓ 环境变量文件已存在${NC}"
fi

# 8. 部署说明
echo ""
echo -e "${GREEN}=========================================="
echo "部署准备完成！"
echo "==========================================${NC}"
echo ""
echo "接下来的步骤："
echo ""
echo "1. 上传项目文件到服务器："
echo "   scp -r /path/to/ethusdt-trading/* root@your-server-ip:/opt/ethusdt-trading/"
echo ""
echo "2. 配置 API Key："
echo "   nano /opt/ethusdt-trading/.env"
echo ""
echo "3. 启动服务："
echo "   cd /opt/ethusdt-trading"
echo "   docker-compose up -d"
echo ""
echo "4. 查看日志："
echo "   docker-compose logs -f"
echo ""
echo "5. 访问应用："
echo "   http://your-server-ip:8501"
echo ""
echo -e "${YELLOW}注意事项：${NC}"
echo "- 确保云服务器安全组开放了 8501 端口"
echo "- 如需使用 AI 功能，请单独部署 Ollama 服务"
echo "- 建议配置 SSL 证书以启用 HTTPS"
echo ""
