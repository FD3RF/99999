# config.py
# 终极完美多空交易系统 - 完整参数配置

# 数据源配置
DATA_SOURCE = "okx"          # 当前主数据源（OKX更稳定）
OKX_SYMBOL = "ETH-USDT"
OKX_INTERVAL = "5m"

# 交易对与时间周期（保留兼容）
SYMBOL = "ETHUSDT"           # Binance交易对格式
INTERVAL = "5m"              # 5分钟K线
KLINE_LIMIT = 100              # 获取K线数量

# MACD标准参数
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# 成交量量化标准（基于20周期均量线）
VOLUME_MA_PERIOD = 20
VOLUME_RATIO_PANIC = 3.0       # 巨量 > 3倍
VOLUME_RATIO_SIGNIFICANT = 2.0 # 显著放量 > 2倍
VOLUME_RATIO_MODERATE = 1.5    # 温和放量 > 1.5倍
VOLUME_RATIO_SHRINK_50 = 0.5   # 极度缩量 < 50%
VOLUME_RATIO_SHRINK_60 = 0.6   # 一般缩量 < 60%

# K线形态参数
LONG_SHADOW_RATIO = 2.0        # 影线长度 ≥ 实体2倍

# 盈亏比要求
MIN_RISK_REWARD_RATIO = 1.5    # 至少盈亏比1:1.5

# 止损偏移量（相对于关键位）
STOP_BUFFER = 0.002            # 0.2% 的缓冲，可根据品种调整

# 横盘定义
RANGE_BAR_COUNT = 8            # 至少8根K线横盘
RANGE_HEIGHT_RATIO = 0.005     # 区间高度小于价格0.5%

# MACD粘合阈值（相对价格）
MACD_CLOSE_RATIO = 0.001       # DIF与DEA差值小于价格的0.1%

# 资金管理
MAX_RISK_PER_TRADE = 0.02      # 单笔最大亏损 ≤ 2%
DEFAULT_POINT_VALUE = 10       # 默认合约点值 (U/点)

# 时间过滤
TRADING_HOURS = [
    (8, 30), (9, 0),           # 早盘活跃期
    (16, 30), (17, 0)          # 晚盘活跃期
]
FORBIDDEN_HOURS = [
    (2, 0), (6, 0)             # 凌晨流动性枯竭时段
]
DATA_PUB_BEFORE = 15           # 数据公布前15分钟禁止交易
DATA_PUB_AFTER = 5             # 数据公布后5分钟禁止交易

# 连续亏损停盘规则
MAX_CONSECUTIVE_LOSS = 2       # 连续亏损2单，休息1小时
MAX_DAILY_LOSS = 3             # 当日连续亏损3单，停止当日交易

# 技术参数
SWING_WINDOW = 5               # 波段识别窗口（左右各5根）
