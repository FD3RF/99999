# ========== 14. Funding Rate 监控 ==========
def get_funding_rate(symbol: str = "ETHUSDT") -> Dict:
    """
    获取资金费率 - 使用 Binance Futures API
    """
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": 1}
        
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                funding_rate = float(data[0]['fundingRate']) * 100
                
                # 判断拥挤度
                if funding_rate > 0.1:
                    status = "多头拥挤"
                    risk = "高"
                elif funding_rate > 0.05:
                    status = "多头偏多"
                    risk = "中"
                elif funding_rate < -0.05:
                    status = "空头偏多"
                    risk = "中"
                elif funding_rate < -0.1:
                    status = "空头拥挤"
                    risk = "高"
                else:
                    status = "平衡"
                    risk = "低"
                
                return {
                    "funding_rate": round(funding_rate, 4),
                    "status": status,
                    "risk": risk,
                    "description": f"{funding_rate:.4f}% ({status})"
                }
    except requests.exceptions.Timeout:
        logger.warning("获取资金费率超时")
    except requests.exceptions.RequestException as e:
        logger.warning(f"获取资金费率失败: {e}")
    except (KeyError, ValueError, IndexError) as e:
        logger.warning(f"解析资金费率失败: {e}")
    
    return {
        "funding_rate": 0,
        "status": "获取中",
        "risk": "低",
        "description": "获取中..."
    }


# ========== 15. Open Interest 监控 ==========
def get_open_interest(symbol: str = "ETHUSDT") -> Dict:
    """
    获取持仓量 - 使用 Binance Futures API
    """
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest"
        params = {"symbol": symbol}
        
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            open_interest = float(data.get('openInterest', 0))
            
            if open_interest > 0:
                status = "高持仓"
            elif open_interest > 500000:
                status = "中等持仓"
            elif open_interest < 200000:
                status = "低持仓"
            
            return {
                "open_interest": open_interest,
                "open_interest_display": f"{open_interest/1000:,.1f}K" if open_interest > 1000000 else f"{open_interest:,.0f} ETH",
                "status": status,
                "description": f"{open_interest:,.0f} ETH ({status})"
            }
    except requests.exceptions.Timeout:
        logger.warning("获取持仓量超时")
    except requests.exceptions.RequestException as e:
        logger.warning(f"获取持仓量失败: {e}")
    except (KeyError, ValueError, IndexError) as e:
        logger.warning(f"解析持仓量失败: {e}")
    
    return {
        "open_interest": 0,
        "open_interest_display": "0",
        "status": "获取中",
        "description": "获取中..."
    }