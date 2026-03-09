# 快速部署指南

## 🚀 一键部署到云服务器

### 前置准备

1. **购买腾讯云 Lighthouse 服务器**
   - 访问：https://console.cloud.tencent.com/lighthouse
   - 配置：2核4G（推荐）或 2核2G
   - 系统：Ubuntu 20.04
   - 价格：¥74/月 或 ¥50/月

2. **记录服务器信息**
   - 公网 IP：例如 `123.45.67.89`
   - 登录密码

### 方式一：Windows 一键部署（推荐）

```cmd
# 双击运行
quick_deploy.bat
```

按提示输入：
- 服务器 IP
- CoinEx API Key

### 方式二：手动部署

#### 1. 连接服务器
```bash
ssh root@your-server-ip
```

#### 2. 运行快速安装
```bash
# 一键安装 Docker 和部署
curl -fsSL https://raw.githubusercontent.com/your-repo/quick-install.sh | bash
```

#### 3. 配置 API Key
```bash
nano /opt/ethusdt-trading/.env
```

#### 4. 启动服务
```bash
cd /opt/ethusdt-trading
docker-compose up -d
```

#### 5. 访问应用
浏览器打开：`http://your-server-ip:8501`

---

## 📋 安全组配置

**必开端口**：
- **22** - SSH（管理）
- **8501** - Streamlit（应用）

**可选端口**：
- **80** - HTTP
- **443** - HTTPS
- **11434** - Ollama AI

### 配置步骤

1. 进入腾讯云控制台
2. 选择实例 → 防火墙
3. 添加规则：

```
协议: TCP
端口: 8501
来源: 0.0.0.0/0
策略: 允许
```

---

## 🎯 完整部署流程（5分钟）

```bash
# 1. 连接服务器
ssh root@your-server-ip

# 2. 安装 Docker
curl -fsSL https://get.docker.com | bash

# 3. 创建项目目录
mkdir -p /opt/ethusdt-trading
cd /opt/ethusdt-trading

# 4. 上传文件（从本地上传）
# 或使用 git clone
git clone https://github.com/your-username/ethusdt-quantitative-system.git .

# 5. 配置 API Key
cat > .env << EOF
COINEX_ACCESS_ID=your_access_id
COINEX_SECRET_KEY=your_secret_key
EOF

# 6. 启动服务
docker-compose up -d

# 7. 检查状态
docker-compose ps
docker-compose logs -f

# 8. 访问应用
# 浏览器打开 http://your-server-ip:8501
```

---

## 🐛 常见问题

### Q1: 无法访问应用

**解决方案**：
```bash
# 检查容器状态
docker-compose ps

# 检查端口
netstat -tulpn | grep 8501

# 查看日志
docker-compose logs -f
```

### Q2: API Key 无效

**解决方案**：
```bash
# 重新配置
nano /opt/ethusdt-trading/.env

# 重启服务
docker-compose restart
```

### Q3: 性能问题

**解决方案**：
- 升级服务器配置
- 检查内存使用：`free -h`
- 检查 CPU 使用：`htop`

---

## 📊 成本估算

| 项目 | 配置 | 价格 |
|------|------|------|
| **推荐** | 2核4G | ¥74/月 |
| 基础 | 2核2G | ¥50/月 |
| 域名 | .com | ¥55/年 |

---

## 📞 获取帮助

- 详细指南：`DEPLOYMENT_GUIDE.md`
- 项目文档：`README.md`
- 诊断工具：`python full_system_diagnostic.py`

---

**预计部署时间：5-10 分钟** ⏱️
