"""
HTML 报告生成模块
基于市场数据生成完整的 A 股行情研判报告，包含：
- 指数 / 涨跌家数 / 板块 / 资金新闻
- 市场情绪仪表盘
- 投资建议（仓位 / 策略 / 风险 / 方向）
- 次日预测展望（情景分析 + 关键位）
全部使用内联 SVG / CSS 可视化，手机端无 CDN 依赖。
"""
import json
import math
import os
import re
from datetime import datetime


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股行情日报 - {report_date}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.6;
    padding: 16px;
    max-width: 680px;
    margin: 0 auto;
}}
.card {{
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}}
h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
h2 {{ font-size: 17px; font-weight: 600; margin-bottom: 14px; color: #222; display: flex; align-items: center; }}
h2::before {{
    content: "";
    display: inline-block;
    width: 4px;
    height: 18px;
    background: #378add;
    border-radius: 2px;
    margin-right: 8px;
}}
.subtitle {{ font-size: 13px; color: #999; margin-bottom: 16px; }}
.holiday-badge {{
    display: inline-block;
    background: #f5f5f5;
    color: #888;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-left: 8px;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th, td {{ padding: 10px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
th {{ background: #fafafa; font-weight: 500; color: #666; font-size: 12px; }}
tr:last-child td {{ border-bottom: none; }}
.up {{ color: #dc2626; font-weight: 600; }}
.down {{ color: #16a34a; font-weight: 600; }}
.neutral {{ color: #666; }}
.tag {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}}
.tag-bullish {{ background: #fef2f2; color: #dc2626; }}
.tag-bearish {{ background: #f0fdf4; color: #16a34a; }}
.tag-neutral {{ background: #f5f5f5; color: #666; }}
.summary-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-top: 14px;
}}
.summary-item {{
    background: #fafafa;
    border-radius: 10px;
    padding: 14px 10px;
    text-align: center;
}}
.summary-item .label {{ font-size: 12px; color: #999; margin-bottom: 6px; }}
.summary-item .value {{ font-size: 20px; font-weight: 700; }}
.bar-container {{ height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden; margin: 10px 0; position: relative; }}
.bar {{ height: 100%; border-radius: 5px; }}
.bar-up {{ background: linear-gradient(90deg, #ef4444, #dc2626); }}
.bar-down {{ background: linear-gradient(90deg, #22c55e, #16a34a); }}
.bar-neutral {{ background: #d4d4d4; }}
.breadth-labels {{ display: flex; justify-content: space-between; font-size: 12px; color: #999; }}
.sector-list {{ margin-top: 10px; }}
.sector-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }}
.sector-row:last-child {{ border-bottom: none; }}
.sector-name {{ color: #333; font-weight: 500; }}
.sector-change {{ font-weight: 600; min-width: 60px; text-align: right; }}
.sector-bar-wrap {{ flex: 1; margin: 0 12px; }}
.news-list {{ margin-top: 8px; }}
.news-item {{ padding: 10px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #444; }}
.news-item:last-child {{ border-bottom: none; }}
.news-item strong {{ color: #222; }}
.alert-box {{
    padding: 12px 14px;
    border-radius: 8px;
    margin-top: 12px;
    font-size: 13px;
    line-height: 1.7;
}}
.alert-warning {{ background: #fffbeb; border-left: 3px solid #f59e0b; color: #92400e; }}
.alert-info {{ background: #eff6ff; border-left: 3px solid #3b82f6; color: #1e40af; }}
.alert-danger {{ background: #fef2f2; border-left: 3px solid #dc2626; color: #991b1b; }}
.section {{ margin-top: 10px; font-size: 13px; color: #555; line-height: 1.8; }}
.footer {{ text-align: center; font-size: 11px; color: #bbb; margin-top: 24px; padding: 12px 0; }}
.mini-note {{ font-size: 12px; color: #999; margin-top: 8px; }}

/* 情绪仪表盘 */
.gauge-wrap {{ display: flex; flex-direction: column; align-items: center; margin: 4px 0 6px; }}
.gauge-label {{ font-size: 13px; color: #666; margin-top: 2px; }}
.gauge-score {{ font-size: 26px; font-weight: 800; margin-top: -6px; }}

/* 投资建议 */
.advice-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 14px; }}
.advice-item {{ background: #fafafa; border-radius: 10px; padding: 12px; text-align: center; }}
.advice-item .label {{ font-size: 12px; color: #999; margin-bottom: 6px; }}
.advice-item .value {{ font-size: 16px; font-weight: 700; }}
.advice-strategy {{ background: #f8fafc; border-radius: 10px; padding: 14px; font-size: 14px; line-height: 1.8; margin-bottom: 12px; }}
.advice-dir {{ font-size: 13px; color: #555; line-height: 1.9; }}
.advice-dir .chip {{
    display: inline-block;
    background: #fff1f0;
    color: #dc2626;
    border: 1px solid #ffccc7;
    border-radius: 12px;
    padding: 2px 10px;
    margin: 2px 4px 0 0;
    font-size: 12px;
}}

/* 预测情景 */
.scenario-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; }}
.scenario {{ border-radius: 10px; padding: 12px 8px; text-align: center; }}
.scenario-bull {{ background: #fef2f2; }}
.scenario-base {{ background: #f5f5f5; }}
.scenario-bear {{ background: #f0fdf4; }}
.scenario .s-title {{ font-size: 12px; color: #888; margin-bottom: 4px; }}
.scenario .s-range {{ font-size: 16px; font-weight: 700; }}
.scenario .s-prob {{ font-size: 11px; color: #999; margin-top: 2px; }}
.level-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }}
.level-row:last-child {{ border-bottom: none; }}
.level-name {{ color: #333; font-weight: 500; }}
.level-val {{ font-weight: 600; }}
.disclaimer {{ font-size: 11px; color: #bbb; line-height: 1.6; margin-top: 10px; }}
</style>
</head>
<body>
<div class="card">
    <h1>A股行情日报</h1>
    <div class="subtitle">报告生成: {generated_at} | 数据来源: {target_date}{weekend_note}</div>
    {market_table}
</div>

<div class="card">
    <h2>市场情绪</h2>
    {sentiment_section}
    <div class="gauge-wrap">
        {gauge_svg}
        <div class="gauge-score {gauge_color_class}">{gauge_score} <span style="font-size:14px;color:#999;font-weight:500;">分</span></div>
        <div class="gauge-label">综合情绪评分（0 极度悲观 ~ 100 极度乐观）</div>
    </div>
    <div class="summary-grid">
        <div class="summary-item">
            <div class="label">涨跌比</div>
            <div class="value {ratio_class}">{up_down_ratio}</div>
        </div>
        <div class="summary-item">
            <div class="label">涨停 / 跌停</div>
            <div class="value">{limit_stats}</div>
        </div>
        <div class="summary-item">
            <div class="label">情绪判定</div>
            <div class="value">{sentiment}</div>
        </div>
        <div class="summary-item">
            <div class="label">周线阶段</div>
            <div class="value">{weekly_stage}</div>
        </div>
    </div>
    {breadth_bar}
</div>

<div class="card">
    <h2>指数表现</h2>
    {index_cards}
    {index_bar}
</div>

<div class="card">
    <h2>领涨行业板块</h2>
    {sector_section}
</div>

<div class="card">
    <h2>投资建议</h2>
    {advice_section}
</div>

<div class="card">
    <h2>次日预测展望</h2>
    {forecast_section}
</div>

<div class="card">
    <h2>资金与新闻</h2>
    {news_section}
</div>

<div class="card">
    <h2>研判与建议</h2>
    {analysis_section}
</div>

<div class="footer">
    本报告由 AI 自动生成，数据来自公开行情，仅供参考，<strong>不构成任何投资建议</strong>。预测部分基于历史规律推断，存在误差，请独立判断。 | {generated_at}
</div>
</body>
</html>"""


def _safe_float(text):
    if text is None:
        return None
    try:
        return float(str(text).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def parse_indices(text: str):
    """从文本提取三大指数数据"""
    indices = []
    names = ["上证指数", "深证成指", "创业板指", "沪深300", "科创50"]
    for name in names:
        pattern = re.compile(
            rf"{re.escape(name)}[^\d]{{0,20}}([\d,\.]+)[^\d\-\+]{{0,15}}([\-\+]?[\d\.]+)%",
            re.S
        )
        m = pattern.search(text)
        if not m:
            pattern2 = re.compile(
                rf"{re.escape(name)}.*?([\d,]{{3,}}(?:\.\d+)?).*?([\-\+]?[\d\.]+)%",
                re.S
            )
            m = pattern2.search(text)
        if m:
            point = m.group(1).replace(",", "")
            change = m.group(2)
            indices.append({
                "name": name,
                "point": point,
                "change": _safe_float(change),
            })
    return indices


def parse_breadth(text: str):
    """提取涨跌家数、涨停跌停数"""
    result = {"up": None, "down": None, "limit_up": None, "limit_down": None}

    up_down = re.search(r"[上]涨[\D]*([\d,]+)[\D]*[下]跌[\D]*([\d,]+)", text)
    if up_down:
        result["up"] = int(up_down.group(1).replace(",", ""))
        result["down"] = int(up_down.group(2).replace(",", ""))
    else:
        up_down2 = re.search(r"([\d,]+)[\D]*家上涨[\D]*([\d,]+)[\D]*家下跌", text)
        if up_down2:
            result["up"] = int(up_down2.group(1).replace(",", ""))
            result["down"] = int(up_down2.group(2).replace(",", ""))

    limit = re.search(r"涨停[\D]*([\d,]+)[\D]*跌停[\D]*([\d,]+)", text)
    if limit:
        result["limit_up"] = int(limit.group(1).replace(",", ""))
        result["limit_down"] = int(limit.group(2).replace(",", ""))

    return result


def parse_sectors(text: str, top_n: int = 8):
    """提取领涨板块"""
    sectors = []
    pattern = re.compile(r"([\u4e00-\u9fa5]{2,8}(?:板块|概念|行业)?)[^\d\-\+]{0,5}([\-\+]?[\d\.]+)%", re.S)
    seen = set()
    for name, change in pattern.findall(text):
        key = name.replace("板块", "").replace("概念", "").replace("行业", "")
        if key in seen:
            continue
        seen.add(key)
        val = _safe_float(change)
        if val is not None and val != 0:
            sectors.append({"name": name.replace("板块", "").replace("概念", "").replace("行业", ""), "change": val})
        if len(sectors) >= top_n:
            break

    if not sectors:
        for line in text.splitlines():
            parts = re.split(r"\s+", line.strip())
            if len(parts) >= 2:
                change = _safe_float(parts[-1])
                if change and abs(change) > 1:
                    name = parts[0]
                    if len(name) >= 2 and "排名" not in name:
                        sectors.append({"name": name, "change": change})
            if len(sectors) >= top_n:
                break

    return sorted(sectors, key=lambda x: abs(x["change"]), reverse=True)[:top_n]


def parse_fund_flow(text: str):
    """提取资金流向关键句"""
    sentences = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(k in line for k in ["流入", "流出", "资金", "主力", "北向", "融资", "买入", "净流入"]):
            if len(line) < 200:
                sentences.append(line)
    return sentences[:6]


def parse_news(text: str):
    """提取新闻要点"""
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 10:
            continue
        if line.startswith("{") or line.startswith("[") or set(line) <= set("-:| "):
            continue
        items.append(line)
    return items[:6]


def parse_technical(text: str):
    """从技术分析文本中提取关键信号"""
    result = {"support": None, "resistance": None, "trend": None, "rsi": None}
    if not text:
        return result

    sup = re.search(r"支撑[位级]?[^\d]{0,12}([\d,\.]+)", text)
    if sup:
        result["support"] = _safe_float(sup.group(1))
    res = re.search(r"压力[位级]?[^\d]{0,12}([\d,\.]+)", text)
    if res:
        result["resistance"] = _safe_float(res.group(1))
    rsi = re.search(r"RSI[^\d]{0,8}([\d\.]+)", text, re.I)
    if rsi:
        result["rsi"] = _safe_float(rsi.group(1))

    if any(k in text for k in ["多头", "上行", "向好", "强势", "金叉"]):
        result["trend"] = "偏多"
    elif any(k in text for k in ["空头", "下行", "走弱", "弱势", "死叉"]):
        result["trend"] = "偏空"
    else:
        result["trend"] = "震荡"
    return result


def compute_outlook(indices, breadth, technical):
    """综合打分模型，输出 0-100 评分与展望"""
    changes = [i["change"] for i in indices if i.get("change") is not None]
    avg = sum(changes) / len(changes) if changes else 0
    up = breadth.get("up") or 0
    down = breadth.get("down") or 0
    total = up + down
    br = up / total if total > 0 else 0.5
    lu = breadth.get("limit_up") or 0
    ld = breadth.get("limit_down") or 0

    score = 50.0
    score += avg * 9
    score += (br - 0.5) * 45
    score += (lu - ld) * 0.15
    if technical.get("trend") == "偏多":
        score += 6
    elif technical.get("trend") == "偏空":
        score -= 6
    rsi = technical.get("rsi")
    if rsi and rsi > 72:
        score -= 10   # 超买，回调压力
    elif rsi and rsi < 28:
        score += 10   # 超卖，反弹可期

    score = max(3, min(97, score))

    if score >= 62:
        outlook = "看多"
    elif score <= 38:
        outlook = "看空"
    else:
        outlook = "震荡"
    return round(score, 0), outlook


def compute_levels(indices, technical):
    """推算主要指数次日关键参考位"""
    levels = []
    for idx in indices[:1]:   # 以上证指数为锚
        point = _safe_float(idx.get("point"))
        if not point:
            continue
        sup = technical.get("support") or round(point * 0.985, 2)
        res = technical.get("resistance") or round(point * 1.015, 2)
        levels.append({"name": idx["name"], "close": point, "support": sup, "resistance": res})
    return levels


def compute_advice(score, outlook, sectors, breadth):
    """给出仓位 / 策略 / 风险 / 方向建议"""
    if score >= 62:
        position = "50% ~ 70%"
        strategy = "顺势适度参与，聚焦主线，但忌追高"
        risk = "中等"
    elif score <= 38:
        position = "10% ~ 30%"
        strategy = "轻仓防御，多看少动，等待企稳信号"
        risk = "偏高"
    else:
        position = "30% ~ 50%"
        strategy = "中性仓位，波段操作为主，留有余地"
        risk = "中等"

    rec = []
    if outlook == "看空":
        rec = ["防御性板块（公用事业 / 医药）", "高股息红利"]
    if sectors:
        rec = [s["name"] for s in sectors[:3]] + rec
    if not rec:
        rec = ["等待方向明朗"]

    return position, strategy, risk, rec


def generate_report(market_data: dict, output_path: str = None) -> str:
    target_date = market_data["target_date"]
    generated_at = market_data["generated_at"]
    data = market_data["data"]

    overview_text = data.get("market_overview", {}).get("text", "")
    sector_text = data.get("sector_ranking", {}).get("text", "")
    fund_text = data.get("fund_flow", {}).get("text", "")
    news_text = data.get("news", {}).get("text", "")
    technical_text = data.get("technical", {}).get("text", "")

    weekend_note = ""
    today = datetime.now()
    if today.weekday() >= 5:
        weekend_note = '<span class="holiday-badge">今日休市</span>'

    indices = parse_indices(overview_text)
    breadth = parse_breadth(overview_text + "\n" + sector_text)
    sectors = parse_sectors(sector_text)
    fund_items = parse_fund_flow(fund_text)
    news_items = parse_news(news_text)
    technical = parse_technical(technical_text)

    score, outlook = compute_outlook(indices, breadth, technical)
    levels = compute_levels(indices, technical)
    position, strategy, risk_level, rec_dirs = compute_advice(score, outlook, sectors, breadth)

    market_table = _build_index_table(indices)
    index_cards = _build_index_cards(indices)
    index_bar = _build_index_bar(indices)
    sentiment_section = _build_sentiment(overview_text, breadth)
    sentiment_text, ratio_class, weekly_stage = _classify_sentiment(breadth, overview_text, technical)
    up_down_ratio, limit_stats = _format_breadth(breadth)
    breadth_bar = _build_breadth_bar(breadth)
    gauge_svg, gauge_color_class = _build_gauge(score, outlook)
    sector_section = _build_sector_chart(sectors)
    advice_section = _build_advice(position, strategy, risk_level, rec_dirs, outlook)
    forecast_section = _build_forecast(score, outlook, levels, technical)
    news_section = _build_news_section(fund_items, news_items)
    analysis_section = _build_analysis(indices, breadth, sectors, overview_text)

    html = REPORT_TEMPLATE.format(
        report_date=target_date,
        generated_at=generated_at,
        target_date=target_date,
        weekend_note=weekend_note,
        market_table=market_table,
        index_cards=index_cards,
        index_bar=index_bar,
        sentiment_section=sentiment_section,
        gauge_svg=gauge_svg,
        gauge_score=int(score),
        gauge_color_class=gauge_color_class,
        sentiment=sentiment_text,
        ratio_class=ratio_class,
        up_down_ratio=up_down_ratio,
        limit_stats=limit_stats,
        weekly_stage=weekly_stage,
        breadth_bar=breadth_bar,
        sector_section=sector_section,
        advice_section=advice_section,
        forecast_section=forecast_section,
        news_section=news_section,
        analysis_section=analysis_section,
    )

    if output_path:
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[INFO] 报告已保存: {output_path}")

    return html


# ----------------------------------------------------------------------------
# 可视化构件
# ----------------------------------------------------------------------------

def _build_gauge(score, outlook):
    """半圆仪表盘（内联 SVG，无外部依赖）"""
    R = 80
    cx, cy = 90, 90
    theta = math.radians(180 * (1 - score / 100))
    xs = cx + R * math.cos(theta)
    ys = cy - R * math.sin(theta)

    if outlook == "看多":
        color, color_class = "#dc2626", "up"
    elif outlook == "看空":
        color, color_class = "#16a34a", "down"
    else:
        color, color_class = "#f59e0b", "neutral"

    svg = f"""
    <svg width="180" height="108" viewBox="0 0 180 108" xmlns="http://www.w3.org/2000/svg">
        <path d="M 10 90 A 80 80 0 0 1 170 90" fill="none" stroke="#eee" stroke-width="12" stroke-linecap="round"/>
        <path d="M 10 90 A 80 80 0 0 1 {xs:.1f} {ys:.1f}" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
        <line x1="90" y1="90" x2="{xs:.1f}" y2="{ys:.1f}" stroke="{color}" stroke-width="3"/>
        <circle cx="90" cy="90" r="5" fill="{color}"/>
        <text x="12" y="104" font-size="10" fill="#bbb">0 悲观</text>
        <text x="138" y="104" font-size="10" fill="#bbb">乐观 100</text>
    </svg>
    """
    return svg, color_class


def _build_index_bar(indices: list) -> str:
    """指数涨跌对比条形图（纯 CSS）"""
    if not indices:
        return ""
    rows = ""
    max_abs = max(abs(i.get("change") or 0) for i in indices) or 1
    for idx in indices:
        change = idx.get("change") or 0
        width = abs(change) / max_abs * 100
        cls = "up" if change > 0 else "down" if change < 0 else "neutral"
        bar_cls = "bar-up" if change > 0 else "bar-down" if change < 0 else "bar-neutral"
        rows += f"""
        <div class="sector-row">
            <span class="sector-name">{idx['name']}</span>
            <div class="sector-bar-wrap">
                <div class="bar-container" style="margin:0;">
                    <div class="bar {bar_cls}" style="width:{width:.1f}%;"></div>
                </div>
            </div>
            <span class="sector-change {cls}">{change:+.2f}%</span>
        </div>
        """
    return f'<div class="mini-note">指数涨跌幅对比</div><div class="sector-list">{rows}</div>'


# ----------------------------------------------------------------------------
# 卡片构件
# ----------------------------------------------------------------------------

def _build_index_table(indices: list) -> str:
    if not indices:
        return '<div class="alert-box alert-info">暂无指数数据，请检查数据来源。</div>'

    rows = ""
    for idx in indices:
        change = idx.get("change")
        cls = "neutral"
        arrow = ""
        if change is not None:
            if change > 0:
                cls = "up"
                arrow = "↑"
            elif change < 0:
                cls = "down"
                arrow = "↓"
        rows += f"""
        <tr>
            <td><strong>{idx['name']}</strong></td>
            <td>{idx.get('point', '--')}</td>
            <td class="{cls}">{change if change is None else f"{change:+.2f}%"} {arrow}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr><th>指数</th><th>收盘</th><th>涨跌幅</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def _build_index_cards(indices: list) -> str:
    if not indices:
        return "<p class='mini-note'>暂无详细指数数据</p>"

    cards = ""
    for idx in indices[:3]:
        change = idx.get("change")
        cls = "neutral"
        if change is not None:
            cls = "up" if change > 0 else "down" if change < 0 else "neutral"
        cards += f"""
        <div class="summary-item" style="margin-bottom:10px;">
            <div class="label">{idx['name']}</div>
            <div class="value">{idx.get('point', '--')}</div>
            <div class="{cls}" style="font-size:14px;margin-top:4px;">{change if change is None else f"{change:+.2f}%"}</div>
        </div>
        """

    return f'<div class="summary-grid">{cards}</div>'


def _build_sentiment(overview: str, breadth: dict) -> str:
    preview = overview[:180] + "..." if len(overview) > 180 else overview
    if not preview:
        preview = "基于当日市场数据综合判断。"
    return f'<div class="section"><p>{preview}</p></div>'


def _classify_sentiment(breadth: dict, overview: str, technical: dict):
    up = breadth.get("up") or 0
    down = breadth.get("down") or 0
    total = up + down

    if total > 0 and up / total > 0.65:
        sentiment = '<span class="tag tag-bullish">偏多</span>'
        stage = "<strong style='color:#dc2626;'>修复</strong>"
        ratio_class = "up"
    elif total > 0 and down / total > 0.55:
        sentiment = '<span class="tag tag-bearish">偏空</span>'
        stage = "<strong style='color:#16a34a;'>调整</strong>"
        ratio_class = "down"
    else:
        sentiment = '<span class="tag tag-neutral">震荡</span>'
        stage = "<strong>观察中</strong>"
        ratio_class = "neutral"

    if "大涨" in overview or "强势" in overview:
        sentiment = '<span class="tag tag-bullish">强势</span>'
        stage = "<strong style='color:#dc2626;'>修复</strong>"
    elif "下跌" in overview and ("跌" in overview[:50] or down > up * 1.3):
        sentiment = '<span class="tag tag-bearish">较弱</span>'
        stage = "<strong style='color:#16a34a;'>下跌</strong>"

    if technical.get("trend") == "偏多":
        stage = "<strong style='color:#dc2626;'>偏多</strong>"
    elif technical.get("trend") == "偏空":
        stage = "<strong style='color:#16a34a;'>偏空</strong>"

    return sentiment, ratio_class, stage


def _format_breadth(breadth: dict):
    up = breadth.get("up")
    down = breadth.get("down")
    limit_up = breadth.get("limit_up")
    limit_down = breadth.get("limit_down")

    ratio = f"{up}:{down}" if up is not None and down is not None else "--"
    limits = f"{limit_up if limit_up is not None else '--'} / {limit_down if limit_down is not None else '--'}"
    return ratio, limits


def _build_breadth_bar(breadth: dict) -> str:
    up = breadth.get("up") or 0
    down = breadth.get("down") or 0
    total = up + down
    if total == 0:
        return ""

    up_pct = round(up / total * 100, 1)
    down_pct = round(down / total * 100, 1)

    return f"""
    <div class="mini-note" style="margin-top:14px;">涨跌家数分布</div>
    <div class="bar-container">
        <div class="bar bar-up" style="width:{up_pct}%;"></div>
    </div>
    <div class="breadth-labels">
        <span class="up">涨 {up_pct}% ({up}家)</span>
        <span class="down">跌 {down_pct}% ({down}家)</span>
    </div>
    """


def _build_sector_chart(sectors: list) -> str:
    if not sectors:
        return '<p class="mini-note">暂未提取到板块数据</p>'

    rows = ""
    max_change = max(abs(s["change"]) for s in sectors) or 1
    for s in sectors:
        pct = abs(s["change"]) / max_change * 100
        cls = "up" if s["change"] > 0 else "down"
        bar_cls = "bar-up" if s["change"] > 0 else "bar-down"
        rows += f"""
        <div class="sector-row">
            <span class="sector-name">{s['name']}</span>
            <div class="sector-bar-wrap">
                <div class="bar-container" style="margin:0;">
                    <div class="bar {bar_cls}" style="width:{pct:.1f}%;"></div>
                </div>
            </div>
            <span class="sector-change {cls}">{s['change']:+.2f}%</span>
        </div>
        """
    return f'<div class="sector-list">{rows}</div>'


def _build_advice(position, strategy, risk_level, rec_dirs, outlook):
    chips = "".join(f'<span class="chip">{d}</span>' for d in rec_dirs)
    out_tag = {"看多": "tag-bullish", "看空": "tag-bearish", "震荡": "tag-neutral"}[outlook]
    return f"""
    <div class="advice-grid">
        <div class="advice-item">
            <div class="label">建议仓位</div>
            <div class="value">{position}</div>
        </div>
        <div class="advice-item">
            <div class="label">风险等级</div>
            <div class="value {('up' if risk_level=='偏高' else 'neutral')}">{risk_level}</div>
        </div>
    </div>
    <div class="advice-strategy">
        <strong>操作策略：</strong>{strategy}
    </div>
    <div class="advice-dir">
        <strong>关注方向：</strong><br>
        {chips}
    </div>
    <div class="alert-box alert-warning">
        <strong>风控提示：</strong>以上为 AI 基于当日数据的量化建议，仅供参考，<strong>不构成投资建议</strong>。请结合自身风险承受能力独立决策。
    </div>
    """


def _build_forecast(score, outlook, levels, technical):
    if outlook == "看多":
        bull, base, bear = "+1.0% ~ +2.5%", "+0.3% ~ +1.0%", "-0.5% ~ -1.0%"
        bull_p, base_p, bear_p = "30%", "45%", "25%"
    elif outlook == "看空":
        bull, base, bear = "0% ~ +1.0%", "-0.5% ~ -1.5%", "-1.5% ~ -3.0%"
        bull_p, base_p, bear_p = "20%", "35%", "45%"
    else:
        bull, base, bear = "+0.5% ~ +1.5%", "-0.5% ~ +0.5%", "-1.0% ~ -2.0%"
        bull_p, base_p, bear_p = "30%", "40%", "30%"

    out_tag = {"看多": "tag-bullish", "看空": "tag-bearish", "震荡": "tag-neutral"}[outlook]
    rsi_note = f"RSI {int(technical['rsi'])}" if technical.get("rsi") else "RSI 数据缺失"
    trend_note = technical.get("trend") or "震荡"

    level_rows = ""
    for lv in levels:
        level_rows += f"""
        <div class="level-row">
            <span class="level-name">{lv['name']} 收盘 {lv['close']}</span>
            <span>
                <span class="level-val down">支撑 {lv['support']}</span>
                <span style="color:#ccc;"> | </span>
                <span class="level-val up">压力 {lv['resistance']}</span>
            </span>
        </div>
        """

    return f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <span class="tag {out_tag}" style="font-size:15px;padding:5px 14px;">次日展望：{outlook}</span>
        <span class="mini-note">技术面：{trend_note} · {rsi_note}</span>
    </div>
    <div class="scenario-grid">
        <div class="scenario scenario-bull">
            <div class="s-title">乐观情景</div>
            <div class="s-range up">{bull}</div>
            <div class="s-prob">概率 {bull_p}</div>
        </div>
        <div class="scenario scenario-base">
            <div class="s-title">基准情景</div>
            <div class="s-range neutral">{base}</div>
            <div class="s-prob">概率 {base_p}</div>
        </div>
        <div class="scenario scenario-bear">
            <div class="s-title">悲观情景</div>
            <div class="s-range down">{bear}</div>
            <div class="s-prob">概率 {bear_p}</div>
        </div>
    </div>
    {level_rows}
    <div class="disclaimer">
        注：情景区间为模型基于动量、广度、技术面综合推断，关键位参考支撑/压力位估算，实际走势受消息面与资金面影响，仅供参考。
    </div>
    """


def _build_news_section(fund_items: list, news_items: list) -> str:
    items = []
    for item in fund_items + news_items:
        item = item.strip()
        if item and item not in items:
            items.append(item)
    items = items[:6]

    if not items:
        return '<p class="mini-note">暂无资金与新闻数据</p>'

    lis = ""
    for item in items:
        lis += f'<div class="news-item">• {item}</div>'
    return f'<div class="news-list">{lis}</div>'


def _build_analysis(indices: list, breadth: dict, sectors: list, overview: str) -> str:
    up = breadth.get("up") or 0
    down = breadth.get("down") or 0
    total = up + down

    notes = []
    if total > 0:
        if up / total > 0.65:
            notes.append("市场涨多跌少，情绪偏多，但连续大涨后注意分化回落。")
        elif down / total > 0.55:
            notes.append("市场跌多涨少，情绪偏空，宜控仓观察，等待超跌反弹信号。")
        else:
            notes.append("涨跌家数分化不大，市场以震荡为主，适合观察为主。")

    if sectors:
        top = sectors[0]
        notes.append(f"领涨方向：<strong>{top['name']}</strong>（{top['change']:+.2f}%），关注其持续性。")

    if indices:
        changes = [i.get("change") for i in indices if i.get("change") is not None]
        if changes:
            avg = sum(changes) / len(changes)
            if avg > 1:
                notes.append("主要指数收盘偏强，短线可适度参与。")
            elif avg < -1:
                notes.append("主要指数收盘较弱，宜保持轻仓。")

    note_html = "<br>".join(notes) if notes else "未能生成有效研判，请结合实时行情判断。"

    return f"""
    <div class="section">
        <p>{note_html}</p>
    </div>
    <div class="alert-box alert-warning">
        <strong>风控提示：</strong>本报告为 AI 自动化生成，仅供参考，不构成投资建议。每日 12:10 自动更新。
    </div>
    """


def generate_email_summary(market_data: dict) -> str:
    target_date = market_data["target_date"]
    generated_at = market_data["generated_at"]
    overview = market_data["data"].get("market_overview", {}).get("text", "")
    indices = parse_indices(overview)
    breadth = parse_breadth(overview)
    technical_text = market_data["data"].get("technical", {}).get("text", "")
    technical = parse_technical(technical_text)
    score, outlook = compute_outlook(indices, breadth, technical)

    idx_summary = "\n".join(
        f"{i['name']}: {i.get('point', '--')} ({i['change']:+.2f}%)" if i.get('change') is not None else f"{i['name']}: {i.get('point', '--')}"
        for i in indices[:3]
    )

    up = breadth.get("up", "--")
    down = breadth.get("down", "--")

    return f"""A股行情日报 - {target_date}
生成时间: {generated_at}

[主要指数]
{idx_summary}

[市场广度]
涨跌比: {up}:{down}

[次日展望] {outlook}（情绪评分 {int(score)}/100）

完整报告请点击下方链接查看。

---
本报告由 AI 自动生成，仅供参考，不构成投资建议。
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "target_date": "2026-07-31",
            "generated_at": "2026-08-01",
            "data": {
                "market_overview": {"text": "上证指数 3832.12 点，涨 0.72%。深证成指 13579.20 点，涨 2.21%。创业板指 3344.50 点，涨 3.06%。全市上涨 4691 家，下跌 728 家，涨停 103 家，跌停 0 家。"},
                "sector_ranking": {"text": "领涨板块：电气设备 4.35%，传媒 3.89%，证券 3.67%，计算机 3.21%，通信 2.98%。"},
                "fund_flow": {"text": "北向资金净流入 56.32 亿元，主力资金净流入 128.5 亿元。金融、科技、新能源获资金青睐。"},
                "news": {"text": "1. 政策面出台促进消费信贷措施。2. 美联储利率保持不变，海外市场回暖。3. 国内重点企业中报预告集中披露。"},
                "technical": {"text": "上证指数处于多头排列，MA5/MA10/MA20 向上发散，MACD 金叉，RSI 62 中性偏强。支撑位 3780，压力位 3900。量能温和放大，短线趋势向好。"},
            },
        }
    output = sys.argv[2] if len(sys.argv) > 2 else "report.html"
    generate_report(data, output)
    print(f"[OK] 报告已生成: {output}")
