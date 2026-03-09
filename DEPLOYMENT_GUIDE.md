# 云服务器部署指南

## 🚀 快速部署（腾讯云 Lighthouse）

### 前置要求
- 腾讯云账号
- 已实名认证
- 充值至少 ¥50（服务器费用）

### 步骤一：创建云服务器

1. **访问腾讯云控制台**
   - 登录：https://console.cloud.tencent.com/lighthouse

2. **创建实例**
   - 地域：推荐广州、上海或北京
   - 镜像：Ubuntu 20.04 LTS
   - 套餐：
     - **入门版**：2核2G（¥50/月）- 基础使用
     - **推荐版**：2核4G（¥74/月）- AI 分析
   - 时长：选择按月计费

3. **配置安全组**
   - 勾选"放通全部端口"或手动添加：
     - TCP 端口 8501（Streamlit）
     - TCP 端口 22（SSH）

4. **确认购买**
   - 记录服务器公网 IP
   - 记录登录密码

### 步骤二：连接服务器

#### Windows 用户（使用 PowerShell）
```powershell
ssh root@your-server-ip
# 输入密码
```

#### Mac/Linux 用户
```bash
ssh root@your-server-ip
# 输入密码
```

### 步骤三：上传项目文件

#### 方式一：使用 SCP（推荐）
```bash
# 在本地电脑执行
scp -r "c:/Users/Administrator/新建文件夹/888" root@your-server-ip:/opt/ethusdt-trading
```

#### 方式二：使用 Git
```bash
# 在服务器上执行
cd /opt
git clone https://github.com/your-username/ethusdt-quantitative-system.git
cd ethusdt-quantitative-system
```

#### 方式三：使用 SFTP 工具
- 工具：FileZilla、WinSCP
- 上传到：`/opt/ethusdt-trading`

### 步骤四：运行部署脚本

```bash
# 在服务器上执行
cd /opt/ethusdt-trading
chmod +x deploy_to_cloud.sh
./deploy_to_cloud.sh
```

### 步骤五：配置 API Key

```bash
# 编辑环境变量文件
nano /opt/ethusdt-trading/.env

# 修改为你的实际密钥
COINEX_ACCESS_ID=ck_ffiiw9tghpmo
COINEX_SECRET_KEY=your_actual_secret_key

# 保存退出（Ctrl+O，回车，Ctrl+X）
```

### 步骤六：启动服务

```bash
cd /opt/ethusdt-trading
docker-compose up -d
```

### 步骤七：验证部署

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 测试访问
curl http://localhost:8501
```

### 步骤八：访问应用

浏览器打开：`http://your-server-ip:8501`

---

## 📋 详细配置

### 1. 配置安全组（腾讯云）

**控制台路径**：实例详情 → 防火墙 → 添加规则

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 22 | 0.0.0.0/0 | SSH |
| TCP | 8501 | 0.0.0.0/0 | Streamlit |
| TCP | 80 | 0.0.0.0/0 | HTTP（可选） |
| TCP | 443 | 0.0.0.0/0 | HTTPS（可选） |

### 2. 配置域名（可选）

#### 2.1 购买域名
- 腾讯云：https://dnspod.cloud.tencent.com/
- 价格：.com 约 ¥55/年

#### 2.2 解析域名
```
类型: A
主机记录: trading
记录值: your-server-ip
```

#### 2.3 配置 Nginx 反向代理

```bash
# 安装 Nginx
apt update
apt install nginx -y

# 配置反向代理
cat > /etc/nginx/sites-available/trading << 'EOF'
server {
    listen 80;
    server_name trading.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用配置
ln -s /etc/nginx/sites-available/trading /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

#### 2.4 配置 SSL 证书（免费）

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 获取证书
certbot --nginx -d trading.yourdomain.com

# 自动续期
certbot renew --dry-run
```

访问：`https://trading.yourdomain.com`

---

## 🤖 部署 AI 服务（可选）

### 方式一：Docker 部署（推荐）

```bash
# 启动 Ollama 容器
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart unless-stopped \
  ollama/ollama

# 下载模型
docker exec -it ollama ollama pull deepseek-r1:1.5b
```

### 方式二：直接安装

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 启动服务
systemctl start ollama
systemctl enable ollama

# 下载模型
ollama pull deepseek-r1:1.5b
```

### 修改应用配置

编辑 `docker-compose.yml`，添加网络连接：

```yaml
services:
  ethusdt-trading:
    # ... 其他配置
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
```

---

## 🔧 常用命令

### Docker 管理
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec ethusdt-trading bash

# 更新代码
git pull
docker-compose down
docker-compose up -d --build
```

### 系统监控
```bash
# CPU 和内存使用
htop

# 磁盘使用
df -h

# 网络连接
netstat -tulpn

# Docker 状态
docker stats
```

### 日志管理
```bash
# 应用日志
tail -f /opt/ethusdt-trading/logs/app.log

# Docker 日志
docker-compose logs -f --tail=100

# 系统日志
journalctl -u docker -f
```

---

## 🐛 故障排除

### 问题 1：无法访问应用

**检查端口**
```bash
# 检查端口监听
netstat -tulpn | grep 8501

# 检查防火墙
ufw status
```

**解决方案**
- 确认安全组开放 8501 端口
- 检查容器是否运行：`docker-compose ps`
- 查看容器日志：`docker-compose logs`

### 问题 2：API Key 无效

**检查配置**
```bash
# 查看环境变量
cat /opt/ethusdt-trading/.env

# 测试 API
curl -X GET "https://api.coinex.com/v1/market/ticker?market=ETHUSDT"
```

### 问题 3：容器启动失败

**查看详细日志**
```bash
# 查看容器状态
docker-compose ps

# 查看完整日志
docker-compose logs --tail=200

# 重新构建
docker-compose down
docker-compose up -d --build
```

### 问题 4：性能问题

**优化建议**
- 升级服务器配置（2核4G）
- 启用 Redis 缓存
- 使用 CDN 加速
- 启用 Gzip 压缩

---

## 💰 成本估算

### 腾讯云 Lighthouse

| 配置 | 价格 | 说明 |
|------|------|------|
| 2核2G | ¥50/月 | 基础使用，无 AI |
| 2核4G | ¥74/月 | 推荐，支持 AI |
| 4核8G | ¥142/月 | 高性能，多用户 |

### 其他费用（可选）

| 项目 | 价格 | 说明 |
|------|------|------|
| 域名 | ¥55/年 | .com 域名 |
| SSL 证书 | 免费 | Let's Encrypt |
| CDN | 按流量计费 | 可选 |

**总计**：¥74/月（推荐配置）

---

## 📞 技术支持

### 相关文档
- [README.md](./README.md) - 项目说明
- [GIT_GUIDE.md](./GIT_GUIDE.md) - Git 使用指南
- [AI_SERVICE_GUIDE.md](./AI_SERVICE_GUIDE.md) - AI 服务配置

### 获取帮助
1. 查看日志：`docker-compose logs -f`
2. 运行诊断：`python full_system_diagnostic.py`
3. 检查网络：`python test_apis_simple.py`

---

**部署完成后，访问 `http://your-server-ip:8501` 即可使用！** 🎉
