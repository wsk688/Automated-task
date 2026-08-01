"""
A股行情数据拉取模块
通过 NeoData API 获取上一交易日市场数据
"""
import json
import os
import urllib.request
import ssl
from datetime import datetime, timedelta


NEODATA_URL = "https://copilot.tencent.com/agenttool/v1/neodata"


def get_token():
    token = os.environ.get("NEODATA_TOKEN")
    if not token:
        raise RuntimeError("请在环境变量中设置 NEODATA_TOKEN")
    return token


def call_neodata(query: str) -> dict:
    token = get_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = json.dumps({
        "query": query,
        "channel": "neodata",
        "sub_channel": "workbuddy",
    }).encode("utf-8")

    ctx = ssl.create_default_context()
    req = urllib.request.Request(NEODATA_URL, data=body, headers=headers, method="POST")

    try:
        resp = urllib.request.urlopen(req, timeout=60, context=ctx)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] NeoData 请求失败: {e}")
        return {"error": str(e)}


def extract_text(data: dict) -> str:
    """从 neodata 返回结果中提取纯文本内容"""
    if isinstance(data, dict):
        if "data" in data:
            return extract_text(data["data"])
        if "text" in data:
            return data["text"]
        if "content" in data:
            return extract_text(data["content"])
        if "answer" in data:
            return data["answer"]
        return json.dumps(data, ensure_ascii=False, indent=2)
    if isinstance(data, list):
        return "\n".join(extract_text(item) for item in data)
    return str(data)


def fetch_all_market_data(target_date: str = None) -> dict:
    """
    拉取完整市场数据
    target_date: 目标日期 (YYYY-MM-DD)，默认为昨天
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"[INFO] 拉取 {target_date} A 股行情数据...")

    queries = {
        "market_overview": f"{target_date} A股大盘行情：上证指数深证成指创业板指收盘点位涨跌幅，两市成交量成交额，涨跌家数统计",
        "sector_ranking": f"{target_date} A股行业板块涨幅排名 概念板块涨幅排名 涨停家数跌停家数 市场热度",
        "fund_flow": f"{target_date} A股北向资金净流入流出 主力资金流向 市场热点新闻",
        "news": f"{target_date} A股市场重大新闻 政策消息 热点事件",
    }

    results = {}
    for key, query in queries.items():
        print(f"[INFO] 查询: {key}")
        raw = call_neodata(query)
        results[key] = {
            "raw": raw,
            "text": extract_text(raw),
        }

    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "target_date": target_date,
        "generated_at": today,
        "is_trading_day": True,  # 默认为交易日，由 generate_report 判断
        "data": results,
    }
