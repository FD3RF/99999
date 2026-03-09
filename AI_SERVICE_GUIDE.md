# AI 服务配置完整指南

## 📊 当前状态

根据诊断结果：
- ✅ Ollama 已安装（v0.17.7）
- ✅ DeepSeek-R1 模型已下载（7B 版本）
- ❌ **CPU 运行太慢** - 超时（30秒未响应）

---

## 🎯 问题根源

### DeepSeek-R1:7B 模型性能要求

| 配置 | CPU 速度 | GPU 速度 |
|------|---------|---------|
| **内存需求** | 8-12 GB | 8-12 GB |
| **响应速度** | 1-2 tokens/秒 | 20-50 tokens/秒 |
| **完成时间** | 60-120 秒 | 3-8 秒 |
| **用户体验** | ❌ 差 | ✅ 好 |

### 你的情况
- **没有 GPU 加速**
- 使用 7B 模型需要 60-120 秒
- 应用超时设置为 15-30 秒
- 结果：总是超时

---

## ✅ 解决方案（按推荐排序）

### 方案一：使用小模型 ⭐⭐⭐ 强烈推荐

**优点**：
- ✅ CPU 也能快速响应（5-10秒）
- ✅ 占用内存小（约 2GB）
- ✅ 效果足够日常使用

**操作步骤**：

```bash
# 1. 下载 1.5B 模型（约 1.5GB）
ollama pull deepseek-r1:1.5b

# 2. 查看已安装模型
ollama list

# 3. 测试运行
ollama run deepseek-r1:1.5b
```

**配置应用**：

在 `app_fixed.py` 中找到（约第 287 行）：
```python
json={"model": "deepseek-r1:7b", ...
```

修改为：
```python
json={"model": "deepseek-r1:1.5b", ...
```

---

### 方案二：增加超时时间 ⚠️ 不推荐

**缺点**：
- ❌ 每次等待 60-120 秒
- ❌ 用户体验极差

**操作步骤**：

在 `app_fixed.py` 中找到：
```python
timeout=15
```

修改为：
```python
timeout=120  # 2分钟
```

---

### 方案三：使用在线 API ⭐⭐ 推荐

**优点**：
- ✅ 秒级响应（1-3秒）
- ✅ 无需本地资源
- ✅ 成本低（约 ¥1/万tokens）

**选项 1：DeepSeek 官方 API**

```bash
# 1. 注册获取 API Key
访问: https://platform.deepseek.com/

# 2. 安装 SDK
pip install openai

# 3. 配置应用
```

修改 `ai_service.py`：
```python
from openai import OpenAI

def get_ai_analysis_online(prompt):
    """使用 DeepSeek 在线 API"""
    client = OpenAI(
        api_key="sk-xxxxxxxx",  # 替换为你的 API Key
        base_url="https://api.deepseek.com"
    )
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200
    )
    
    return response.choices[0].message.content
```

**选项 2：其他免费 API**

- **Google Gemini**: https://makersuite.google.com/
- **Claude**: https://console.anthropic.com/
- **通义千问**: https://dashscope.aliyun.com/

---

### 方案四：添加 GPU 加速 💪 最佳体验

**如果你有 NVIDIA 显卡**：

```bash
# 1. 检查显卡驱动
nvidia-smi

# 2. 安装 CUDA 工具包
访问: https://developer.nvidia.com/cuda-downloads

# 3. 重启 Ollama
ollama serve

# 4. 测试性能
ollama run deepseek-r1:7b
```

**预期效果**：
- 响应时间：3-8 秒
- 可以使用大模型
- 体验最佳

---

## 🚀 快速实施（推荐方案一）

### 步骤 1：下载小模型

```bash
ollama pull deepseek-r1:1.5b
```

等待下载完成（约 1.5GB，需 5-10 分钟）

### 步骤 2：修改应用

打开 `app_fixed.py`，找到第 287 行：

```python
# 原代码
json={"model": "deepseek-r1:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
timeout=15

# 修改为
json={"model": "deepseek-r1:1.5b", "prompt": prompt, "stream": False, "options": {"temperature": 0.3, "num_predict": 100}},
timeout=30
```

### 步骤 3：重启应用

```bash
# 停止旧应用
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *streamlit*"

# 启动应用
streamlit run app_fixed.py
```

### 步骤 4：测试效果

在应用中触发 AI 分析，应该 5-10 秒内得到响应。

---

## 📈 性能对比

| 方案 | 响应时间 | 成本 | 推荐度 |
|------|---------|------|--------|
| **小模型(1.5B)** | 5-10秒 | 免费 | ⭐⭐⭐⭐⭐ |
| **大模型+GPU** | 3-8秒 | 免费 | ⭐⭐⭐⭐ |
| **在线API** | 1-3秒 | ¥1/万tokens | ⭐⭐⭐⭐ |
| **大模型+CPU** | 60-120秒 | 免费 | ⭐ |

---

## 🔧 故障排除

### 问题1：模型下载慢

```bash
# 使用国内镜像
set OLLAMA_MIRRORS=https://ollama.ai.cloudflare.com
ollama pull deepseek-r1:1.5b
```

### 问题2：内存不足

```bash
# 检查内存使用
# Windows: 任务管理器
# 或命令行
systeminfo | findstr "可用物理内存"

# 如果内存 < 8GB，必须用 1.5B 模型
```

### 问题3：仍然超时

```bash
# 增加 num_predict 限制输出长度
"num_predict": 50  # 更短的输出

# 或进一步增加超时
timeout=60
```

### 问题4：AI 响应质量差

```python
# 调整温度参数
"temperature": 0.1  # 更保守（默认 0.3）

# 或增加输出长度
"num_predict": 200  # 更详细的回答
```

---

## 💡 最佳实践

### 混合模式（推荐）

```python
# 在应用中添加模式选择
mode = st.radio("AI 模式", ["快速", "详细"])

if mode == "快速":
    model = "deepseek-r1:1.5b"
    timeout = 15
else:
    model = "deepseek-r1:7b"
    timeout = 120
```

### 自动降级

```python
def get_ai_analysis(prompt):
    try:
        # 先尝试快速模型
        return call_model("deepseek-r1:1.5b", timeout=15)
    except Timeout:
        # 自动降级到更短输出
        return call_model("deepseek-r1:1.5b", timeout=30, max_tokens=50)
```

---

## 📞 需要帮助？

如果遇到问题，请提供：
1. 系统配置（CPU、内存、GPU）
2. `ollama list` 输出
3. 错误信息截图

我会帮你选择最适合的方案！
