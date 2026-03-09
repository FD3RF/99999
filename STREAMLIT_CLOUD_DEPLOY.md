# Streamlit Community Cloud 部署指南

## ✨ 为什么选择 Streamlit Cloud？

- ✅ **完全免费** - 无限期免费使用
- ✅ **官方支持** - Streamlit 官方托管平台
- ✅ **自动部署** - 连接 GitHub 自动部署
- ✅ **HTTPS 域名** - 自动分配 SSL 证书
- ✅ **Python 环境** - 完整的 Python 运行时
- ✅ **无需信用卡** - 无需任何付费

---

## 🚀 一键部署步骤（5分钟）

### 步骤 1：推送到 GitHub

```bash
# 1. 在 GitHub 创建仓库
# 访问：https://github.com/new
# 仓库名：ethusdt-quantitative-system
# 设为 Public（必须公开才能免费）

# 2. 添加远程仓库
cd c:\Users\Administrator\新建文件夹\888
git remote add origin https://github.com/你的用户名/ethusdt-quantitative-system.git

# 3. 推送代码
git push -u origin master
```

### 步骤 2：连接 Streamlit Cloud

1. 访问：https://share.streamlit.io/
2. 使用 GitHub 账号登录
3. 点击 "New app"

### 步骤 3：配置应用

```
Repository: 你的用户名/ethusdt-quantitative-system
Branch: master
Main file path: app_coinex.py
```

点击 "Deploy!"

### 步骤 4：配置 Secrets（API Key）

在 Streamlit Cloud 中：
1. 进入应用设置
2. 点击 "Secrets"
3. 添加：

```toml
COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"
COINEX_SECRET_KEY = "your_secret_key_here"
```

4. 保存并重新部署

### 步骤 5：访问应用

部署成功后，你会获得一个免费域名：
```
https://你的应用名-你的用户名.streamlit.app
```

---

## 📋 完整自动化脚本

### Windows 一键部署脚本

创建 `deploy_to_streamlit_cloud.bat`：

```batch
@echo off
echo ========================================
echo Streamlit Cloud 自动部署
echo ========================================
echo.

echo [1/5] 检查 Git 远程仓库
git remote -v | findstr origin
if errorlevel 1 (
    echo 需要配置 GitHub 仓库
    set /p GITHUB_USER="请输入 GitHub 用户名: "
    git remote add origin https://github.com/%GITHUB_USER%/ethusdt-quantitative-system.git
)

echo.
echo [2/5] 推送代码到 GitHub
git push -u origin master

echo.
echo [3/5] 部署完成！
echo.
echo 接下来请：
echo 1. 访问 https://share.streamlit.io/
echo 2. 使用 GitHub 登录
echo 3. 点击 "New app"
echo 4. 选择你的仓库和 app_coinex.py
echo 5. 点击 "Deploy!"
echo.
echo 访问地址将是：
echo https://ethusdt-quantitative-system-你的用户名.streamlit.app
echo.
pause
```

---

## ⚙️ 项目配置文件

已创建以下文件以支持 Streamlit Cloud：

### `.streamlit/config.toml`（已创建）
```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

### `requirements.txt`（已创建）
```
streamlit
pandas
requests
plotly
pyttsx3
```

### `packages.txt`（可选，系统依赖）
```
ffmpeg
espeak
```

---

## 🔐 配置 Secrets

### 方式一：Web 界面（推荐）

1. 在 Streamlit Cloud 应用页面
2. 点击 "Settings" → "Secrets"
3. 添加：

```toml
# CoinEx API
COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"
COINEX_SECRET_KEY = "your_secret_key"

# 可选：其他交易所
KUCOIN_API_KEY = "your_kucoin_key"
KUCOIN_SECRET = "your_kucoin_secret"
```

### 方式二：文件配置（本地测试）

创建 `.streamlit/secrets.toml`：
```toml
COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"
COINEX_SECRET_KEY = "your_secret_key"
```

---

## 🤖 AI 服务配置

Streamlit Cloud **不支持** Ollama 本地部署，但你有两个选择：

### 选项 1：使用在线 AI API

修改 `app_coinex.py`，使用在线 API：

```python
# 使用 DeepSeek API
def get_ai_analysis_online(prompt):
    import openai
    client = openai.OpenAI(
        api_key=st.secrets.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

获取 DeepSeek API Key：https://platform.deepseek.com/
- 新用户免费额度：¥10
- 价格：¥1/百万 tokens

### 选项 2：禁用 AI 功能

在应用中添加开关：

```python
if st.checkbox("启用 AI 分析"):
    ai_report = get_ai_analysis_online(prompt)
else:
    ai_report = "AI 功能已禁用"
```

---

## 📊 资源限制

Streamlit Community Cloud 免费限制：

| 资源 | 限制 | 说明 |
|------|------|------|
| **应用数量** | 3 个 | 可创建 3 个应用 |
| **内存** | 1GB | 每个 应用 |
| **CPU** | 共享 | 多应用共享 |
| **存储** | 临时 | 重启后清空 |
| **带宽** | 无限制 | 足够使用 |
| **运行时间** | 无限制 | 长期运行 |

---

## 🔄 自动更新

### 自动部署触发条件

- ✅ 推送到 master 分支
- ✅ 修改 requirements.txt
- ✅ 更新 Streamlit 配置

### 手动触发重新部署

在 Streamlit Cloud 界面：
1. 进入应用详情
2. 点击 "Reboot" 或 "Redeploy"

---

## 🌐 自定义域名（可选）

### 步骤

1. 准备域名（如：trading.yourdomain.com）
2. 在 Streamlit Cloud 设置中添加域名
3. 配置 DNS CNAME 记录：
   ```
   CNAME trading your-app.streamlit.app
   ```
4. 等待 DNS 生效

---

## 🐛 常见问题

### Q1: 部署失败 - 依赖安装错误

**解决方案**：
```bash
# 检查 requirements.txt
cat requirements.txt

# 指定版本号
streamlit==1.28.0
pandas==2.0.3
requests==2.31.0
plotly==5.17.0
```

### Q2: 应用启动慢

**原因**：Streamlit Cloud 需要安装依赖

**解决方案**：
- 使用缓存 `@st.cache_data`
- 减少依赖包数量
- 使用轻量级库

### Q3: API Key 无效

**解决方案**：
```bash
# 检查 Secrets 配置
# 确保格式正确，没有多余空格

# 正确格式：
COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"

# 错误格式：
COINEX_ACCESS_ID = ck_ffiiw9tghpmo  # 缺少引号
```

### Q4: AI 功能不工作

**原因**：Streamlit Cloud 不支持 Ollama

**解决方案**：
- 使用在线 API（DeepSeek/OpenAI）
- 或在应用中禁用 AI 功能

---

## 📱 部署成功检查清单

- [ ] 代码已推送到 GitHub
- [ ] GitHub 仓库设为 Public
- [ ] 在 Streamlit Cloud 创建应用
- [ ] 选择正确的 Python 文件
- [ ] 配置 Secrets（API Key）
- [ ] 应用成功启动
- [ ] 数据正常显示
- [ ] 访问域名可用

---

## 💰 成本：完全免费！

| 项目 | 价格 |
|------|------|
| Streamlit Cloud | **免费** |
| GitHub 仓库 | **免费** |
| 域名 | 免费子域名 |
| SSL 证书 | **免费** |
| **总计** | **¥0** |

---

## 🚀 立即开始

### 快速部署命令

```bash
# 1. 添加 GitHub 远程仓库
cd c:\Users\Administrator\新建文件夹\888
git remote add origin https://github.com/你的用户名/ethusdt-quantitative-system.git

# 2. 推送代码
git push -u origin master

# 3. 访问 Streamlit Cloud
# https://share.streamlit.io/

# 4. 连接 GitHub 并部署
```

---

## 📞 获取帮助

- Streamlit 文档：https://docs.streamlit.io/streamlit-community-cloud
- 部署指南：https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app
- 故障排除：查看应用日志

---

**这是最简单、最快速的免费部署方案！** 🎉
