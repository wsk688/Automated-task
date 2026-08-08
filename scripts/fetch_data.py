"""
A股行情数据拉取模块（真实行情，免 token）
=================================================
- 指数（上证/深证/创业板/沪深300/科创50）：腾讯财经 qt.gtimg.cn 实时接口
- 涨跌家数 / 涨停跌停 / 行业板块排行 / 主力资金流入个股：东方财富 push2 公开接口
- 容错设计：东方财富若短时不可用，自动降级（指数仍来自腾讯），绝不崩溃
- 全部使用 Python 标准库（urllib/ssl/json），GitHub Actions 无需安装第三方依赖

注意：东方财富接口对高频请求有限流。本模块在 GitHub Actions 上每天仅运行一次，
且内置 3 次退避重试，生产环境稳定可用。
"""
import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime

CTX = ssl.create_default_context()

# 腾讯指数代码映射（显示名 -> 腾讯代码）
TENCENT_INDICES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "沪深300": "sh000300",
    "科创50": "sh000688",
}

# 东方财富 clist 基础地址（主 + 备）
EM_HOSTS = [
    "https://push2.eastmoney.com/api/qt",
    "https://push2his.eastmoney.com/api/qt",
    "https://82.push2.eastmoney.com/api/qt",
]

# 全 A 股票范围（沪A + 深A + 创业板 + 科创板），用于涨跌家数统计
EM_FS_ALL = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
# 行业板块
EM_FS_SECTOR = "m:90+t:2"


def _http_get(url: str, ref: str = "https://quote.eastmoney.com/", timeout: int = 25, retries: int = 3):
    """带退避重试的 GET 请求，返回解码文本。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": ref,
    }
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_err or RuntimeError("request failed")


# ---------------------------------------------------------------------------
# 腾讯：指数实时行情
# ---------------------------------------------------------------------------
def fetch_indices_tencent() -> list:
    """返回 [ {name, code, price, change_abs, change_pct} ... ]"""
    codes = ["s_" + c for c in TENCENT_INDICES.values()]
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    raw = _http_get(url, ref="https://gu.qq.com/")
    result = []
    code_to_name = {v: k for k, v in TENCENT_INDICES.items()}
    for line in raw.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        var_name, val = line.split("=", 1)
        code = var_name.replace("v_", "").replace("s_", "").strip()
        parts = val.strip('"').split("~")
        # s_ 格式: 1~名称~代码~现价~涨跌绝对值~涨跌幅%~成交量~成交额~...
        try:
            price = float(parts[3])
            change_abs = float(parts[4]) if parts[4] not in ("", "-") else 0.0
            change_pct = float(parts[5]) if parts[5] not in ("", "-") else 0.0
        except (IndexError, ValueError):
            continue
        result.append({
            "name": code_to_name.get(code, code),
            "code": code,
            "price": price,
            "change_abs": round(change_abs, 2),
            "change_pct": round(change_pct, 2),
        })
    return result


# ---------------------------------------------------------------------------
# 东方财富：结构化行情
# ---------------------------------------------------------------------------
def _em_clist(fs: str, fields: str, pz: int = 6000) -> list:
    """调用东方财富 clist 接口，返回 diff 列表。自动轮换主机。"""
    last_err = None
    ts = int(time.time() * 1000)
    for host in EM_HOSTS:
        url = (
            f"{host}/clist/get?pn=1&pz={pz}&po=1&np=1&fltt=2&invt=2"
            f"&fs={urllib.parse.quote(fs)}&fields={fields}&_={ts}"
        )
        try:
            raw = _http_get(url, ref="https://quote.eastmoney.com/")
            d = json.loads(raw)
            diff = (d.get("data") or {}).get("diff") or []
            if diff:
                return diff
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    if last_err:
        raise last_err
    return []


def fetch_breadth_em() -> dict:
    """全 A 涨跌家数 + 涨停/跌停统计（近似：涨跌幅>=9.85% 视为涨停）。"""
    rows = _em_clist(EM_FS_ALL, "f12,f14,f3")
    up = dn = flat = lu = ld = 0
    for r in rows:
        c = r.get("f3")
        if c is None:
            flat += 1
            continue
        if c > 0:
            up += 1
        elif c < 0:
            dn += 1
        else:
            flat += 1
        if c >= 9.85:
            lu += 1
        elif c <= -9.85:
            ld += 1
    total = up + dn + flat
    return {
        "up": up, "down": dn, "flat": flat,
        "limit_up": lu, "limit_down": ld, "total": total,
    }


def fetch_sectors_em(top_n: int = 12) -> list:
    """行业板块涨幅排行（含主力净流入，单位：亿元）。"""
    rows = _em_clist(EM_FS_SECTOR, "f12,f14,f3,f62", pz=80)
    rows = [r for r in rows if isinstance(r.get("f3"), (int, float))]
    rows.sort(key=lambda r: r["f3"], reverse=True)
    out = []
    for r in rows[:top_n]:
        out.append({
            "name": r.get("f14", ""),
            "change_pct": round(r["f3"], 2),
            "main_inflow": round((r.get("f62") or 0) / 1e8, 2),  # 元 -> 亿
        })
    return out


def fetch_inflow_stocks_em(top_n: int = 12) -> list:
    """主力资金净流入排行（单位：亿元）。"""
    rows = _em_clist(EM_FS_ALL, "f12,f14,f3,f62", pz=6000)
    rows = [r for r in rows if isinstance(r.get("f62"), (int, float)) and r["f62"] > 0]
    rows.sort(key=lambda r: r["f62"], reverse=True)
    out = []
    for r in rows[:top_n]:
        out.append({
            "name": r.get("f14", ""),
            "code": r.get("f12", ""),
            "change_pct": round(r.get("f3") or 0, 2),
            "main_inflow": round(r["f62"] / 1e8, 2),
        })
    return out


def fetch_limitup_stocks_em(top_n: int = 15) -> list:
    """涨停个股（涨跌幅>=9.85%）列表。"""
    rows = _em_clist(EM_FS_ALL, "f12,f14,f3", pz=6000)
    rows = [r for r in rows if isinstance(r.get("f3"), (int, float)) and r["f3"] >= 9.85]
    rows.sort(key=lambda r: r["f3"], reverse=True)
    return [{
        "name": r.get("f14", ""),
        "code": r.get("f12", ""),
        "change_pct": round(r["f3"], 2),
    } for r in rows[:top_n]]


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------
def fetch_all_market_data(target_date: str = None) -> dict:
    """
    拉取完整市场数据，返回结构化 dict。
    target_date: 数据日期（默认运行当天）。
    """
    now = datetime.now()
    if target_date is None:
        target_date = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M")

    # 指数（腾讯，主锚点，优先获取）
    indices = []
    try:
        indices = fetch_indices_tencent()
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] 腾讯指数获取失败: {e}")

    # 东方财富结构化数据（涨跌家数 / 板块 / 资金 / 涨停）
    breadth = None
    sectors = []
    inflow_stocks = []
    limitup_stocks = []
    em_ok = True
    em_error = ""
    try:
        breadth = fetch_breadth_em()
        sectors = fetch_sectors_em()
        inflow_stocks = fetch_inflow_stocks_em()
        limitup_stocks = fetch_limitup_stocks_em()
        print("[INFO] 东方财富结构化数据获取成功")
    except Exception as e:  # noqa: BLE001
        em_ok = False
        em_error = str(e)
        print(f"[WARN] 东方财富数据获取失败，降级运行: {e}")

    data = {
        "indices": indices,
        "breadth": breadth,
        "sectors": sectors,
        "main_inflow_stocks": inflow_stocks,
        "limitup_stocks": limitup_stocks,
        "em_ok": em_ok,
        "em_error": em_error,
    }
    return {
        "target_date": target_date,
        "generated_at": generated_at,
        "is_trading_day": now.weekday() < 5,
        "data": data,
    }


if __name__ == "__main__":
    market = fetch_all_market_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(market, f, ensure_ascii=False, indent=2)
    d = market["data"]
    print(f"target_date={market['target_date']} em_ok={d['em_ok']}")
    print(f"indices={len(d['indices'])} breadth={d['breadth']}")
    print(f"sectors={len(d['sectors'])} inflow={len(d['main_inflow_stocks'])} limitup={len(d['limitup_stocks'])}")
