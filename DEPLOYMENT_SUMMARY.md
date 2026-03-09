# 🚀 云服务器部署 - 完整方案

## ✅ 已完成准备

### Git 仓库
- ✅ 代码已提交（4 次提交）
- ✅ 文件完整（37 个文件）
- ✅ 配置齐全（Docker + 部署脚本）

### 部署配置
- ✅ Dockerfile（容器化配置）
- ✅ docker-compose.yml（服务编排）
- ✅ deploy_to_cloud.sh（自动化部署脚本）
- ✅ quick_deploy.bat（Windows 一键部署）
- ✅ .env.example（环境变量模板）

### 文档
- ✅ DEPLOYMENT_GUIDE.md（详细部署指南）
- ✅ DEPLOY_QUICK.md（快速部署指南）
- ✅ README.md（项目文档）

---

## 🎯 三种部署方式

### 方式一：一键部署（最简单）⭐

**适合人群**：Windows 用户，新手推荐

**步骤**：
1. 购买腾讯云 Lighthouse 服务器（2核4G，¥74/月）
2. 双击运行 `quick_deploy.bat`
3. 按提示输入服务器信息和 API Key
4. 等待部署完成
5. 访问 `http://your-server-ip:8501`

**预计时间**：5-10 分钟

---

### 方式二：半自动部署（推荐）⭐⭐

**适合人群**：有基础用户，快速部署

**步骤**：

#### 1. 购买服务器
```
访问：https://console.cloud.tencent.com/lighthouse
配置：Ubuntu 20.04，2核4G
记录：公网 IP 和登录密码
```

#### 2. 连接服务器
```bash
ssh root@your-server-ip
```

#### 3. 运行部署脚本
```bash
# 下载并运行
curl -fsSL https://raw.githubusercontent.com/your-repo/deploy_to_cloud.sh | bash
```

#### 4. 上传文件
```bash
# 在本地执行
scp -r "c:/Users/Administrator/新建文件夹/888" root@your-server-ip:/opt/ethusdt-trading
```

#### 5. 配置 API Key
```bash
# 在服务器执行
nano /opt/ethusdt-trading/.env
```

输入：
```
COINEX_ACCESS_ID=ck_ffiiw9tghpmo
COINEX_SECRET_KEY=your_secret_key
```

#### 6. 启动服务
```bash
cd /opt/ethusdt-trading
docker-compose up -d
```

#### 7. 访问应用
浏览器打开：`http://your-server-ip:8501`

---

### 方式三：手动部署（高级）

**适合人群**：运维人员，自定义配置

详见：`DEPLOYMENT_GUIDE.md`

---

## 📋 部署清单

### 云服务器购买

| 平台 | 配置 | 价格 | 推荐 |
|------|------|------|------|
| **腾讯云 Lighthouse** | 2核4G | ¥74/月 | ⭐⭐⭐⭐⭐ |
| 腾讯云 Lighthouse | 2核2G | ¥50/月 | ⭐⭐⭐⭐ |
| 阿里云 ECS | 2核4G | ¥80/月 | ⭐⭐⭐ |
| AWS EC2 | t3.medium | $30/月 | ⭐⭐⭐ |

### 必备配置

- ✅ 操作系统：Ubuntu 20.04 / 22.04
- ✅ 内存：≥2GB（推荐 4GB）
- ✅ 存储：≥40GB
- ✅ 带宽：≥3Mbps

### 安全组规则

| 协议 | 端口 | 说明 | 必须 |
|------|------|------|------|
| TCP | 22 | SSH | ✅ |
| TCP | 8501 | Streamlit | ✅ |
| TCP | 80 | HTTP | 可选 |
| TCP | 443 | HTTPS | 可选 |
| TCP | 11434 | Ollama AI | 可选 |

---

## 💰 成本估算

### 月度费用

| 项目 | 配置 | 价格 |
|------|------|------|
| **云服务器** | 2核4G | ¥74/月 |
| 域名 | .com | ¥55/年 |
| SSL 证书 | Let's Encrypt | 免费 |
| 流量 | 按量计费 | 约 ¥10/月 |
| **总计** | - | **~¥90/月** |

### 优化建议

- 使用包年套餐：享 8 折优惠
- 使用竞价实例：节省 60-80%
- 启用 CDN：降低流量成本

---

## 🔧 部署后配置

### 1. 配置域名（可选）

```bash
# 安装 Nginx
apt install nginx -y

# 配置反向代理
nano /etc/nginx/sites-available/trading
```

### 2. 配置 SSL（推荐）

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 获取证书
certbot --nginx -d trading.yourdomain.com
```

### 3. 启用 AI 服务（可选）

```bash
# 部署 Ollama
docker run -d -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull deepseek-r1:1.5b
```

### 4. 设置自动备份

```bash
# 创建备份脚本
nano /opt/backup.sh
chmod +x /opt/backup.sh

# 添加到 crontab
crontab -e
# 每天凌晨 2 点备份
0 2 * * * /opt/backup.sh
```

---

## 📊 性能优化

### 应用优化

- ✅ 启用 Gzip 压缩
- ✅ 配置 Redis 缓存
- ✅ 启用 CDN 加速
- ✅ 优化数据库查询

### 服务器优化

```bash
# 优化内核参数
sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_max_syn_backlog=65535

# 优化文件描述符
ulimit -n 65535
```

---

## 🐛 故障排除

### 问题诊断流程

```bash
# 1. 检查容器状态
docker-compose ps

# 2. 查看日志
docker-compose logs -f

# 3. 检查端口
netstat -tulpn | grep 8501

# 4. 测试 API
curl http://localhost:8501/_stcore/health

# 5. 运行诊断
python full_system_diagnostic.py
```

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| 无法访问 | 检查安全组端口 8501 |
| 容器启动失败 | 查看日志 `docker-compose logs` |
| API Key 无效 | 检查 .env 文件配置 |
| 性能慢 | 升级服务器配置 |

---

## 📞 获取帮助

### 文档资源
- [快速部署指南](./DEPLOY_QUICK.md) - 5分钟快速上手
- [详细部署指南](./DEPLOYMENT_GUIDE.md) - 完整配置说明
- [项目文档](./README.md) - 功能介绍
- [Git 使用指南](./GIT_GUIDE.md) - 版本管理

### 诊断工具
```bash
# 系统诊断
python full_system_diagnostic.py

# 网络测试
python test_apis_simple.py

# AI 服务测试
python diagnose_ai.py
```

---

## ✅ 部署完成检查清单

- [ ] 云服务器已购买
- [ ] 安全组规则已配置
- [ ] 项目文件已上传
- [ ] API Key 已配置
- [ ] Docker 服务已启动
- [ ] 应用可正常访问
- [ ] 数据正常显示
- [ ] AI 功能正常（可选）
- [ ] 域名已配置（可选）
- [ ] SSL 证书已安装（可选）

---

## 🎉 开始部署

### 推荐流程

**新手用户**：
1. 双击 `quick_deploy.bat`
2. 按提示完成部署

**有经验用户**：
1. 阅读 `DEPLOY_QUICK.md`
2. 5 分钟完成部署

**运维人员**：
1. 阅读 `DEPLOYMENT_GUIDE.md`
2. 自定义配置

---

**选择适合你的方式，开始部署吧！** 🚀
