import streamlit as st
import requests
import time

# ========== AI 配置 ==========
@st.cache_data
def get_ai_config():
    """获取 AI 配置"""
    return {
        "model": st.secrets.get("AI_MODEL", "deepseek-r1:1.5b"),  # 默认使用小模型
        "timeout": int(st.secrets.get("AI_TIMEOUT", "30")),  # 默认30秒超时
        "max_tokens": int(st.secrets.get("AI_MAX_TOKENS", "200")),  # 限制输出长度
        "temperature": 0.3
    }

def get_ai_analysis(prompt, use_fast=True):
    """
    AI 分析函数（优化版）
    
    参数:
        prompt: 分析提示词
        use_fast: 是否使用快速模式（小模型 + 短输出）
    """
    try:
        config = get_ai_config()
        
        # 快速模式：使用小模型
        model = "deepseek-r1:1.5b" if use_fast else config["model"]
        max_tokens = 100 if use_fast else config["max_tokens"]
        timeout = 15 if use_fast else config["timeout"]
        
        # 显示正在使用的模型
        print(f"使用模型: {model}, 超时: {timeout}s")
        
        start_time = time.time()
        
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config["temperature"],
                    "num_predict": max_tokens  # 限制生成 token 数
                }
            },
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        print(f"AI 响应时间: {elapsed:.1f}s")
        
        if resp.status_code == 200:
            response = resp.json().get("response", "")
            
            if response:
                # 添加模型信息
                model_info = f"\n\n_模型: {model} | 响应时间: {elapsed:.1f}s_"
                return response + model_info
            else:
                return "AI 返回空响应"
        else:
            return f"AI 服务错误: HTTP {resp.status_code}"
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return f"⏱️ AI 响应超时 ({elapsed:.0f}s)\n\n**建议**:\n1. 使用快速模式\n2. 或切换到 1.5B 模型"
        
    except requests.exceptions.ConnectionError:
        return "❌ AI 服务未启动\n\n**启动方法**:\n```bash\nollama serve\n```"
        
    except Exception as e:
        return f"AI 分析失败: {str(e)}"

def get_ai_analysis_fast(market_data):
    """
    快速 AI 分析（优化版）
    使用小模型 + 短输出，确保 5-10 秒内响应
    """
    price = market_data.get('price', 0)
    trend = market_data.get('trend', '未知')
    vol_ratio = market_data.get('vol_ratio', 1.0)
    imbalance = market_data.get('imbalance', 0)
    signals = market_data.get('signals', [])
    resonance = market_data.get('resonance', '无')
    
    # 简化的提示词（减少 token 数）
    prompt = f"""分析 ETHUSDT:
价格:{price:.0f} 趋势:{trend} 量比:{vol_ratio:.1f} 盘口:{imbalance:.2f}
信号:{','.join(signals[:3])} 共振:{resonance}

简要给出:
1. 判断(吸筹/派发/震荡)
2. 操作建议
3. 风险(高/中/低)

限制在100字内。"""

    return get_ai_analysis(prompt, use_fast=True)

def get_ai_analysis_full(market_data):
    """
    完整 AI 分析
    使用大模型 + 详细输出，需要等待 30-60 秒
    """
    price = market_data.get('price', 0)
    trend = market_data.get('trend', '未知')
    vol_ratio = market_data.get('vol_ratio', 1.0)
    imbalance = market_data.get('imbalance', 0)
    signals = market_data.get('signals', [])
    resonance = market_data.get('resonance', '无')
    support = market_data.get('support', '无')
    resistance = market_data.get('resistance', '无')
    
    # 详细的提示词
    prompt = f"""作为量化交易员，分析 ETHUSDT 数据：

**市场数据**:
- 当前价格: ${price:.2f}
- 趋势: {trend}
- 量比: {vol_ratio:.2f}
- 盘口失衡: {imbalance:.2f}

**技术信号**:
- 触发信号: {', '.join(signals) if signals else '无'}
- 共振状态: {resonance}
- 支撑位: {support}
- 压力位: {resistance}

请给出详细分析：
1. 市场结构判断 (吸筹/派发/震荡) 及理由
2. 关键操作建议 (入场点/止损/止盈)
3. 风险等级评估 (高/中/低) 及应对策略
4. 未来 1-4 小时走势预测

请用专业但易懂的语言回答。"""

    return get_ai_analysis(prompt, use_fast=False)

# ========== AI 模型管理 ==========
def list_available_models():
    """列出可用的 DeepSeek 模型"""
    models = [
        {"name": "deepseek-r1:1.5b", "size": "1.5GB", "speed": "⚡⚡⚡ 快", "quality": "⭐⭐ 基础", "recommended": True},
        {"name": "deepseek-r1:7b", "size": "4.7GB", "speed": "⚡ 慢", "quality": "⭐⭐⭐ 好", "recommended": False},
        {"name": "deepseek-r1:8b", "size": "5.3GB", "speed": "⚡ 很慢", "quality": "⭐⭐⭐⭐ 很好", "recommended": False},
    ]
    return models

def check_model_status():
    """检查已安装的模型"""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            installed = [m['name'] for m in data.get('models', [])]
            return installed
    except:
        pass
    return []

# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试
    print("测试 AI 服务...")
    
    test_data = {
        'price': 2024.45,
        'trend': '上涨',
        'vol_ratio': 0.41,
        'imbalance': -0.09,
        'signals': ['价格站上MA20'],
        'resonance': '无共振',
        'support': 2020,
        'resistance': 2030
    }
    
    print("\n=== 快速分析（推荐）===")
    result = get_ai_analysis_fast(test_data)
    print(result)
    
    print("\n=== 可用模型 ===")
    for model in list_available_models():
        status = "✅ 已安装" if model['name'] in check_model_status() else "⬇️ 未安装"
        rec = "⭐ 推荐" if model['recommended'] else ""
        print(f"{status} {model['name']} - {model['size']} - {model['speed']} - {model['quality']} {rec}")
