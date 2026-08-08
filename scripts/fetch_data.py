"""
A股行情数据拉取模块（真实行情）
=================================================
数据源优先级：
1. 指数（上证/深证/创业板/沪深300/科创50）：腾讯 qt.gtimg.cn 实时接口（公网CDN，云端稳定）
2. 涨跌家数 / 涨停跌停 / 行业板块 / 主力资金：Tushare 专业 API（需 token，云端稳定可靠）
   - 若未配置 TUSHARE_TOKEN，则降级使用东方财富 push2 公开接口（云端可能不稳定）
3. 全部使用 Python 标准库（urllib/ssl/json），GitHub Actions 无需安装第三方依赖

Tushare 免费注册：https://tushare.pro/register  （手机号验证后获得 token）
将 token 配置到 GitHub Secrets 的 TUSHARE_TOKEN 即可。
"""
import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

CTX = ssl.create_default_context()

# 腾讯指数代码映射（显示名 -> 腾讯代码）
TENCENT_INDICES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "沪深300": "sh000300",
    "科创50": "sh000688",
}

# Tushare 指数代码（显示名 -> Tushare ts_code）
TUSHARE_INDICES = {
    "上证指数": "000001.SH",
    "深证成指": "399001.SZ",
    "创业板指": "399006.SZ",
    "沪深300": "000300.SH",
    "科创50": "000688.SH",
}

# 申万一级行业指数（31个，Tushare ts_code）— 用于板块排行
SW_INDUSTRIES = [
    ("农林牧渔", "801010.SI"), ("基础化工", "801030.SI"), ("钢铁", "801040.SI"),
    ("有色金属", "801050.SI"), ("电子", "801080.SI"), ("家用电器", "801110.SI"),
    ("食品饮料", "801120.SI"), ("纺织服饰", "801130.SI"), ("轻工制造", "801140.SI"),
    ("医药生物", "801150.SI"), ("公用事业", "801160.SI"), ("交通运输", "801170.SI"),
    ("房地产", "801180.SI"), ("商贸零售", "801200.SI"), ("社会服务", "801210.SI"),
    ("综合", "801230.SI"), ("建筑材料", "801710.SI"), ("建筑装饰", "801720.SI"),
    ("电力设备", "801730.SI"), ("国防军工", "801740.SI"), ("计算机", "801750.SI"),
    ("传媒", "801760.SI"), ("通信", "801770.SI"), ("银行", "801780.SI"),
    ("非银金融", "801790.SI"), ("汽车", "801880.SI"), ("机械设备", "801890.SI"),
    ("煤炭", "801950.SI"), ("石油石化", "801960.SI"), ("环保", "801970.SI"),
    ("美容护理", "801980.SI"),
]

# 东方财富 clist 基础地址（降级备用）
EM_HOSTS = [
    "https://push2.eastmoney.com/api/qt",
    "https://push2his.eastmoney.com/api/qt",
    "https://82.push2.eastmoney.com/api/qt",
]
EM_FS_ALL = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
EM_FS_SECTOR = "m:90+t:2"


def _http_get(url: str, ref: str = "https://quote.eastmoney.com/", timeout: int = 25, retries: int = 3):
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


def get_last_trade_date() -> str:
    """返回最近交易日（YYYYMMDD）。周末回退到周五。"""
    now = datetime.now()
    d = now.date()
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# Tushare：专业行情 API（云端稳定，需 token）
# ---------------------------------------------------------------------------
def _tushare(api_name: str, params: dict, fields: str = None, timeout: int = 30):
    """调用 Tushare API，返回 data dict（含 fields/items）。自动处理分页。"""
    token = os.environ.get("TUSHARE_TOKEN", "")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN 未配置")
    url = "http://api.tushare.pro"
    all_items = []
    all_fields = None
    offset = 0
    limit = 5000
    while True:
        payload = {
            "api_name": api_name,
            "token": token,
            "params": params,
            "limit": limit,
            "offset": offset,
        }
        if fields:
            payload["fields"] = fields
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("code") != 0:
            raise RuntimeError(f"Tushare {api_name} 错误: {result.get('msg')}")
        d = result["data"]
        if all_fields is None:
            all_fields = d.get("fields", [])
        items = d.get("items", [])
        all_items.extend(items)
        if not d.get("has_more") or len(items) < limit:
            break
        offset += limit
        time.sleep(0.2)  # 限速保护
    return {"fields": all_fields, "items": all_items}


def fetch_breadth_tushare(trade_date: str) -> dict:
    """全 A 涨跌家数 + 涨停/跌停统计。"""
    d = _tushare("daily", {"trade_date": trade_date}, fields="ts_code,pct_chg")
    fields = d["fields"]
    pct_idx = fields.index("pct_chg")
    up = dn = flat = lu = ld = 0
    for it in d["items"]:
        c = it[pct_idx]
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
    return {"up": up, "down": dn, "flat": flat, "limit_up": lu, "limit_down": ld, "total": total}


def fetch_sectors_tushare(trade_date: str) -> list:
    """申万一级行业涨幅排行。"""
    out = []
    for name, code in SW_INDUSTRIES:
        try:
            d = _tushare("index_daily", {"trade_date": trade_date, "ts_code": code},
                         fields="pct_chg")
            if d["items"]:
                pct = d["items"][0][d["fields"].index("pct_chg")]
                out.append({"name": name, "change_pct": round(pct, 2), "main_inflow": 0.0})
            time.sleep(0.15)
        except Exception:
            continue
    out.sort(key=lambda r: r["change_pct"], reverse=True)
    return out[:12]


def fetch_inflow_stocks_tushare(trade_date: str) -> list:
    """主力资金净流入排行（个股）。"""
    try:
        d = _tushare("moneyflow", {"trade_date": trade_date},
                     fields="ts_code,net_mf_amount")
        fields = d["fields"]
        net_idx = fields.index("net_mf_amount")
        rows = []
        for it in d["items"]:
            net = it[net_idx]
            if net is None:
                continue
            rows.append({"code": it[0], "main_inflow": round(net / 1e8, 2)})  # 元->亿
        rows.sort(key=lambda r: r["main_inflow"], reverse=True)
        # 补充涨跌幅
        dd = _tushare("daily", {"trade_date": trade_date}, fields="ts_code,pct_chg")
        pct_map = {it[0]: it[dd["fields"].index("pct_chg")] for it in dd["items"]}
        for r in rows[:12]:
            r["change_pct"] = round(pct_map.get(r["code"]) or 0, 2)
            r["name"] = r["code"]  # 代码代替名称（无额外接口调用）
        return rows[:12]
    except Exception as e:
        print(f"[WARN] Tushare 资金流获取失败: {e}")
        return []


# ---------------------------------------------------------------------------
# 东方财富：降级备用（云端可能不稳定）
# ---------------------------------------------------------------------------
def _em_clist(fs: str, fields: str, pz: int = 6000) -> list:
    last_err = None
    ts = int(time.time() * 1000)
    for host in EM_HOSTS:
        url = (f"{host}/clist/get?pn=1&pz={pz}&po=1&np=1&fltt=2&invt=2"
               f"&fs={urllib.parse.quote(fs)}&fields={fields}&_={ts}")
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
    return {"up": up, "down": dn, "flat": flat, "limit_up": lu, "limit_down": ld, "total": total}


def fetch_sectors_em(top_n: int = 12) -> list:
    rows = _em_clist(EM_FS_SECTOR, "f12,f14,f3,f62", pz=80)
    rows = [r for r in rows if isinstance(r.get("f3"), (int, float))]
    rows.sort(key=lambda r: r["f3"], reverse=True)
    out = []
    for r in rows[:top_n]:
        out.append({
            "name": r.get("f14", ""),
            "change_pct": round(r["f3"], 2),
            "main_inflow": round((r.get("f62") or 0) / 1e8, 2),
        })
    return out


def fetch_inflow_stocks_em(top_n: int = 12) -> list:
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


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------
def fetch_all_market_data(target_date: str = None) -> dict:
    now = datetime.now()
    if target_date is None:
        target_date = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M")
    trade_date = get_last_trade_date()

    # 指数（腾讯，主锚点，优先获取）
    indices = []
    try:
        indices = fetch_indices_tencent()
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] 腾讯指数获取失败: {e}")

    # 结构化数据（涨跌家数 / 板块 / 资金）
    breadth = None
    sectors = []
    inflow_stocks = []
    src = "none"
    em_ok = True
    em_error = ""

    use_tushare = bool(os.environ.get("TUSHARE_TOKEN"))
    try:
        if use_tushare:
            src = "tushare"
            breadth = fetch_breadth_tushare(trade_date)
            sectors = fetch_sectors_tushare(trade_date)
            inflow_stocks = fetch_inflow_stocks_tushare(trade_date)
            print("[INFO] Tushare 数据获取成功")
        else:
            src = "eastmoney"
            breadth = fetch_breadth_em()
            sectors = fetch_sectors_em()
            inflow_stocks = fetch_inflow_stocks_em()
            print("[INFO] 东方财富数据获取成功")
    except Exception as e:  # noqa: BLE001
        em_ok = False
        em_error = str(e)
        print(f"[WARN] 主数据源({src})失败，尝试降级: {e}")
        # 降级到东财（若主源是东财则失败；若主源是Tushare则降级到东财）
        if use_tushare:
            try:
                breadth = fetch_breadth_em()
                sectors = fetch_sectors_em()
                inflow_stocks = fetch_inflow_stocks_em()
                src = "eastmoney(fallback)"
                em_ok = True
                print("[INFO] 降级到东方财富成功")
            except Exception as e2:
                em_ok = False
                em_error = f"Tushare: {e} | 东财: {e2}"
                print(f"[ERROR] 所有数据源均失败: {em_error}")

    data = {
        "indices": indices,
        "breadth": breadth,
        "sectors": sectors,
        "main_inflow_stocks": inflow_stocks,
        "em_ok": em_ok,
        "em_error": em_error,
        "data_source": src,
    }
    return {
        "target_date": target_date,
        "trade_date": trade_date,
        "generated_at": generated_at,
        "is_trading_day": now.weekday() < 5,
        "data": data,
    }


if __name__ == "__main__":
    market = fetch_all_market_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(market, f, ensure_ascii=False, indent=2)
    d = market["data"]
    print(f"target_date={market['target_date']} trade_date={market['trade_date']} src={d['data_source']}")
    print(f"indices={len(d['indices'])} breadth={d['breadth']}")
    print(f"sectors={len(d['sectors'])} inflow={len(d['main_inflow_stocks'])}")
