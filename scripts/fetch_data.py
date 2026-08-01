"""
A股行情数据拉取模块
通过 NeoData API 获取上一交易日市场数据，并解析为结构化文本
"""
import json
import os
import re
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


def extract_text(data) -> str:
    """
    递归从 neodata 返回结果中提取可读文本。
    优先顺序：text > answer > content > 列表拼接 > JSON 字符串
    """
    if data is None:
        return ""
    if isinstance(data, str):
        return data.strip()
    if isinstance(data, (int, float, bool)):
        return str(data)
    if isinstance(data, list):
        parts = [extract_text(item) for item in data]
        return "\n".join(p for p in parts if p).strip()
    if isinstance(data, dict):
        # 优先取语义化字段
        for key in ("text", "answer", "content", "markdown", "summary", "result"):
            if key in data and data[key]:
                return extract_text(data[key])
        # 如果只有 apiData / data 等包装字段，继续递归
        for key in ("data", "apiData", "result", "payload", "response"):
            if key in data and data[key]:
                return extract_text(data[key])
        # 兜底：把所有值拼接
        parts = []
        for v in data.values():
            t = extract_text(v)
            if t:
                parts.append(t)
        return "\n".join(parts).strip()
    return str(data)


def clean_text(text: str) -> str:
    """清理文本，去除重复 JSON 片段"""
    if not text:
        return ""
    # 去掉明显是 JSON 的长串
    text = re.sub(r'\{["\']?\w*["\']?\s*:\s*\{.*?\}\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\[\s*\{.*?\}\s*\]', '', text, flags=re.DOTALL)
    # 合并多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def fetch_all_market_data(target_date: str = None) -> dict:
    """
    拉取完整市场数据
    target_date: 目标日期 (YYYY-MM-DD)，默认为昨天
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"[INFO] 拉取 {target_date} A 股行情数据...")

    queries = {
        "market_overview": f"{target_date} A股大盘行情：上证指数、深证成指、创业板指收盘点位和涨跌幅，两市成交量、成交额、涨跌家数统计",
        "sector_ranking": f"{target_date} A股行业板块涨幅排名、概念板块涨幅排名、涨停家数、跌停家数",
        "fund_flow": f"{target_date} A股北向资金净流入流出、主力资金流向、市场热点新闻",
        "news": f"{target_date} A股市场重大新闻、政策消息、热点事件",
    }

    results = {}
    for key, query in queries.items():
        print(f"[INFO] 查询: {key}")
        raw = call_neodata(query)
        text = clean_text(extract_text(raw))
        results[key] = {
            "raw": raw,
            "text": text,
        }
        print(f"[INFO] {key} 文本长度: {len(text)}")

    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "target_date": target_date,
        "generated_at": today,
        "is_trading_day": True,
        "data": results,
    }
