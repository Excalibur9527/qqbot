"""
每日功能通用工具
统一8点刷新逻辑
"""

from datetime import datetime, timedelta


def get_daily_seed_date() -> str:
    """
    获取用于每日随机种子的日期字符串
    每天早上8点刷新，8点前算前一天
    """
    now = datetime.now()
    # 如果当前时间在8点之前，使用前一天的日期
    if now.hour < 8:
        seed_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        seed_date = now.strftime("%Y-%m-%d")
    return seed_date


def get_daily_seed(user_id: str, group_id: str = "") -> str:
    """
    生成每日随机种子字符串
    同一天（8点刷新）同一用户结果相同
    """
    date_str = get_daily_seed_date()
    if group_id:
        return f"{user_id}_{group_id}_{date_str}"
    return f"{user_id}_{date_str}"
