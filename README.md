# ETHUSDT 全网节点量化系统

## 🎯 系统特点

✅ **多交易所支持**：KuCoin → Gate.io → Binance → OKX → CoinGecko  
✅ **智能切换**：自动选择最快可用节点  
✅ **代理支持**：支持 HTTP/HTTPS 代理配置  
✅ **兜底方案**：CoinGecko 保证不掉线  
✅ **实时分析**：K线图、MA均线、订单簿、AI审计  

## 🚀 快速启动

### 方法一：交互式启动（推荐新手）
```bash
双击 start_menu.bat
选择启动方式
```

### 方法二：直接启动
```bash
streamlit run app_v3.py
```

### 方法三：配置代理启动

**Windows CMD:**
```cmd
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
streamlit run app_v3.py
```

**Windows PowerShell:**
```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
streamlit run app_v3.py
```

## 📊 数据源优先级

1. **KuCoin** - 国内可直接访问
2. **Gate.io** - 国内可直接访问  
3. **Binance** - 需代理或稳定网络
4. **OKX** - 需代理或稳定网络
5. **CoinGecko** - 兜底方案（仅价格）

## 🔧 代理配置

### Clash 默认端口
- HTTP: 7890
- SOCKS5: 7891

### V2Ray 默认端口
- HTTP: 10809
- SOCKS5: 10808

### Shadowsocks 默认端口
- HTTP: 1087
- SOCKS5: 1086

## 🧠 AI 分析功能

### 启用 AI 审计（可选）
```bash
# 安装 Ollama
# 访问: https://ollama.com/download

# 启动服务
ollama serve

# 下载模型
ollama pull deepseek-r1:7b

# 重启 Streamlit 应用
```

## 📱 功能说明

### 实时监控
- 5分钟K线图
- MA20/MA50均线
- 大单墙检测
- 订单簿深度分析

### 智能信号
- 价格站上MA20
- 巨量异动（2倍均量）
- 买盘/卖盘压倒
- 多头/空头共振

### AI 审计
- 市场结构判断
- 操作建议
- 风险评级
- 语音播报

## ⚠️ 故障排除

### 问题：所有节点连接失败

**解决方案 1：配置代理**
```bash
set HTTPS_PROXY=http://127.0.0.1:7890
streamlit run app_v3.py
```

**解决方案 2：检查防火墙**
- 临时关闭 Windows 防火墙
- 允许 Python 通过防火墙

**解决方案 3：使用 VPN**
- 连接海外节点
- 重启应用

### 问题：数据加载慢

**原因**：正在尝试多个节点  
**解决**：等待几秒，系统会自动切换到最快节点

### 问题：AI 分析不工作

**原因**：Ollama 服务未启动  
**解决**：
```bash
ollama serve
ollama pull deepseek-r1:7b
```

## 📂 文件说明

```
.
├── app_v3.py           # 主程序（推荐使用）
├── app_v2.py           # 旧版本
├── app.py              # 初始版本
├── start_menu.bat      # 交互式启动器
├── test_apis_simple.py # 网络测试工具
├── requirements.txt    # 依赖列表
└── README.md           # 说明文档
```

## 🔍 测试网络连接

```bash
python test_apis_simple.py
```

输出示例：
```
[OK] KuCoin            456ms
[OK] Gate.io           832ms
[OK] Binance Main      416ms
...
```

## 📈 性能优化

- ✅ 数据缓存：5秒内重复请求自动缓存
- ✅ 自动刷新：每10秒更新数据
- ✅ 连接池复用：减少TCP握手开销
- ✅ 智能重试：自动退避重试机制

## 💡 使用建议

1. **首次使用**：先运行 `test_apis_simple.py` 测试网络
2. **网络受限**：使用代理或VPN
3. **稳定性优先**：选择 KuCoin 或 Gate.io
4. **数据分析**：结合AI建议，理性决策

## 📞 技术支持

如遇问题，请检查：
1. 网络连接是否正常
2. 代理配置是否正确
3. Python 版本 >= 3.8
4. 依赖包是否完整安装

---

**免责声明**：本系统仅供学习和研究使用，不构成投资建议。加密货币交易存在风险，请谨慎决策。
