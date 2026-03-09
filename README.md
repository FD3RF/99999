# ETHUSDT 机构级量化巡航系统

> 企业级实时交易监控系统 | 多交易所支持 | AI 智能分析

## ✨ 核心特性

### 🌐 多数据源支持
- **CoinEx** - 企业级 API，稳定快速 ⭐ 推荐
- **KuCoin** - 国内可直接访问
- **Gate.io** - 国内可直接访问
- **Binance/OKX** - 备用节点
- **智能切换** - 自动选择最快可用节点

### 🤖 AI 智能分析
- **DeepSeek-R1** 本地部署
- **1.5B 模型** - 快速响应（7-10秒）⚡
- **7B 模型** - 深度分析（需 GPU）
- 自动生成交易建议和风险评级

### 📊 专业级功能
- ✅ 实时 K 线图（5分钟周期）
- ✅ MA20/MA50 均线分析
- ✅ 订单簿深度监控
- ✅ 大单墙智能识别
- ✅ 量比异动检测
- ✅ 多空情绪判断
- ✅ 10秒自动刷新

## 🚀 快速启动

### 前置要求
```bash
Python >= 3.8
pip install -r requirements.txt
```

### 方式一：CoinEx 企业版（推荐）⭐
```bash
# 1. 配置 API Key
# 创建 .streamlit/secrets.toml 文件，内容：
# COINEX_ACCESS_ID = "your_access_id"
# COINEX_SECRET_KEY = "your_secret_key"

# 2. 启动应用
streamlit run app_coinex.py
# 或双击 launch_coinex.bat
```

### 方式二：多交易所版本
```bash
streamlit run app_fixed.py
# 或双击 launch_fixed.bat
```

### 方式三：带代理启动
```cmd
# Windows CMD
set HTTPS_PROXY=http://127.0.0.1:7890
streamlit run app_coinex.py

# PowerShell
$env:HTTPS_PROXY="http://127.0.0.1:7890"
streamlit run app_coinex.py
```

## 📁 项目结构

```
.
├── app_coinex.py              # CoinEx 企业版 ⭐ 推荐
├── app_fixed.py               # KuCoin/Gate.io 版本
├── app_v3.py                  # 多交易所版本
├── app_multi_key.py           # 多 API Key 版本
│
├── .streamlit/
│   ├── config.toml           # Streamlit 配置
│   └── secrets.toml          # API 密钥（需创建）
│
├── requirements.txt          # Python 依赖
├── README.md                 # 项目文档
│
├── launch_coinex.bat         # CoinEx 启动脚本
├── launch_fixed.bat          # Fixed 启动脚本
├── launch_multi_key.bat      # Multi-Key 启动脚本
│
├── diagnose.py               # 诊断工具
├── diagnose_ai.py            # AI 诊断工具
├── full_system_diagnostic.py # 完整系统诊断
├── test_apis_simple.py       # API 测试工具
└── AI_SERVICE_GUIDE.md       # AI 服务指南
```

## 🎯 版本对比

| 版本 | 数据源 | AI 支持 | 特点 | 推荐度 |
|------|--------|---------|------|--------|
| **app_coinex.py** | CoinEx | ✅ 快速 | 企业级、稳定、专业 | ⭐⭐⭐⭐⭐ |
| **app_fixed.py** | KuCoin/Gate.io | ✅ 快速 | 多交易所、免费 | ⭐⭐⭐⭐ |
| **app_multi_key.py** | 多 Key | ✅ 快速 | 负载均衡 | ⭐⭐⭐⭐ |
| app_v3.py | 多交易所 | ⚠️ 慢 | 原始版本 | ⭐⭐⭐ |

## 🔧 配置说明

### API Key 配置

创建 `.streamlit/secrets.toml` 文件：

```toml
# CoinEx API（推荐）
COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"
COINEX_SECRET_KEY = "your_secret_key_here"

# 可选：多个 API Key（负载均衡）
COINEX_ACCESS_ID_2 = "your_second_access_id"
COINEX_SECRET_KEY_2 = "your_second_secret_key"
```

### AI 服务配置

#### 方式一：快速模型（推荐）⚡
```bash
# 安装 Ollama
# 访问: https://ollama.com/download

# 启动服务
ollama serve

# 下载快速模型（1.1GB，CPU 可用）
ollama pull deepseek-r1:1.5b
```

#### 方式二：深度模型（需 GPU）
```bash
# 下载大模型（4.9GB）
ollama pull deepseek-r1:7b
```

#### 方式三：在线 API（无需本地部署）
```bash
# 注册 DeepSeek API
# https://platform.deepseek.com/

# 修改 ai_service.py 中的配置
DEEPSEEK_API_KEY = "your_api_key"
```

## 📊 功能详解

### 1. 实时行情监控
- K 线图（5分钟周期）
- MA20/MA50 均线
- 成交量柱状图
- 大单墙标记（支撑/阻力）

### 2. 订单簿深度分析
- 买卖盘力量对比
- 盘口失衡度计算
- 大单墙智能识别
- 市场情绪判断（多头/空头/均衡）

### 3. 技术指标
- **MA20/MA50**: 趋势判断
- **量比**: 放量/缩量识别
- **盘口失衡**: 多空力量对比
- **大单墙**: 支撑/阻力位

### 4. 智能信号
- ✅ 价格站上 MA20
- ✅ 巨量异动（量比 > 2.0）
- ✅ 买盘/卖盘压倒
- ✅ 多头/空头共振

### 5. AI 智能审计
- 市场结构判断（吸筹/派发/震荡）
- 操作建议（入场/止损/止盈）
- 风险等级（高/中/低）
- 语音播报关键信号

## 🔍 诊断工具

### 测试网络连接
```bash
python test_apis_simple.py
```

### 测试 AI 服务
```bash
python diagnose_ai.py
```

### 完整系统诊断
```bash
python full_system_diagnostic.py
```

### 诊断报告示例
```
[OK] CoinEx API          442ms
[OK] KuCoin API          387ms
[OK] Gate.io API          661ms
[OK] Binance API          427ms
[OK] DeepSeek AI           11ms

测试项目: 8/8 通过
系统状态: 完全健康 ✅
```

## ⚙️ 高级配置

### 代理设置

常用代理端口：
- **Clash**: 7890 (HTTP), 7891 (SOCKS5)
- **V2Ray**: 10809 (HTTP), 10808 (SOCKS5)
- **Shadowsocks**: 1087 (HTTP), 1086 (SOCKS5)

### 缓存配置
```python
# K线缓存：5秒，最多10个
@st.cache_data(ttl=5, max_entries=10)

# 订单簿缓存：2秒，最多5个
@st.cache_data(ttl=2, max_entries=5)
```

### 性能优化
- 向量化数据处理
- 连接池复用
- 自动重试机制
- 节点轮询策略

## 🐛 故障排除

### 问题 1：无法获取数据

**症状**：显示"网络连接失败"

**解决方案**：
1. 运行诊断工具：`python test_apis_simple.py`
2. 检查网络连接
3. 配置代理（如需要）
4. 尝试使用 CoinEx 版本（更稳定）

### 问题 2：AI 分析超时

**症状**：显示"AI 服务未启动"或超时

**解决方案**：
1. 确认 Ollama 运行：`ollama serve`
2. 使用快速模型：`ollama pull deepseek-r1:1.5b`
3. 检查模型是否下载：`ollama list`
4. 增加超时时间（在代码中修改 timeout 参数）

### 问题 3：缓存错误

**症状**：Streamlit 缓存相关错误

**解决方案**：
```bash
# 清除 Streamlit 缓存
streamlit cache clear

# 重启应用
streamlit run app_coinex.py
```

### 问题 4：端口被占用

**症状**：显示"Port 8501 is already in use"

**解决方案**：
```bash
# Windows
netstat -ano | findstr :8501
taskkill /F /PID <PID>

# 或使用其他端口
streamlit run app_coinex.py --server.port 8502
```

## 📈 使用建议

### 交易策略
1. **观察趋势**：结合 MA20/MA50 判断大方向
2. **关注量能**：量比 > 2.0 表示异动
3. **参考盘口**：失衡度 > 0.4 为明显信号
4. **AI 辅助**：结合 AI 建议理性决策

### 风险管理
- ⚠️ 本系统仅供学习和研究使用
- ⚠️ 不构成投资建议
- ⚠️ 加密货币交易存在风险
- ⚠️ 请谨慎决策，理性投资

## 🔄 更新日志

### v1.3.0 (当前版本)
- ✅ 新增 CoinEx 企业级支持
- ✅ 优化 AI 模型（1.5B 快速响应）
- ✅ 企业级缓存优化
- ✅ 完整诊断工具集
- ✅ 多 API Key 支持

### v1.2.0
- ✅ 多交易所支持
- ✅ 智能节点切换
- ✅ 代理配置支持

### v1.1.0
- ✅ AI 智能分析
- ✅ 大单墙识别
- ✅ 订单簿深度分析

### v1.0.0
- ✅ 基础 K 线图
- ✅ MA 均线分析
- ✅ 实时监控

## 📞 技术支持

### 系统要求
- Python >= 3.8
- 操作系统：Windows/Linux/macOS
- 内存：>= 4GB（AI 模型需要额外 2-5GB）
- 网络：稳定互联网连接

### 依赖包
```
streamlit
pandas
requests
plotly
pyttsx3 (语音播报，可选)
```

### 获取帮助
1. 查看诊断报告：`python full_system_diagnostic.py`
2. 检查网络连接：`python test_apis_simple.py`
3. 查看 AI 服务指南：`AI_SERVICE_GUIDE.md`

## 📜 开源协议

MIT License

---

**免责声明**：本系统仅供学习和研究使用，不构成投资建议。加密货币交易存在风险，请谨慎决策。使用本系统产生的任何损失，开发者不承担责任。

**祝交易顺利！** 🎉
