"""
HTML 报告生成模块（消费结构化真实行情）
=================================================
输入：fetch_data.fetch_all_market_data() 返回的结构化 dict
输出：自包含 HTML（内联 SVG/CSS，无外部 CDN 依赖，手机端友好）
包含：指数 / 涨跌家数 / 板块 / 资金动向 / 涨停股 / 情绪仪表盘 / 投资建议 / 次日展望
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
    <div class="subtitle">数据日期: {target_date} | 生成: {generated_at}{weekend_note}</div>
    {degrade_note}
    {market_table}
</div>

<div class="card">
    <h2>市场情绪</h2>
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
    <h2>资金动向</h2>
    {fund_section}
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
    <h2>研判与建议</h2>
    {analysis_section}
</div>

<div class="footer">
    本报告由 AI 自动生成，数据来自公开行情（腾讯财经 / 东方财富），仅供参考，<strong>不构成任何投资建议</strong>。预测部分基于历史规律推断，存在误差，请独立判断。 | {generated_at}
</div>
</body>
</html>"""


def _safe(v):
    return v if isinstance(v, (int, float)) else None


def compute_outlook(indices, breadth):
    """综合打分：指数平均涨跌 + 涨跌家数比例 + 涨停/跌停差。"""
    changes = [i["change_pct"] for i in indices if _safe(i.get("change_pct")) is not None]
    avg = sum(changes) / len(changes) if changes else 0.0

    score = 50.0
    score += avg * 9
    if breadth and breadth.get("total"):
        up = breadth["up"] or 0
        down = breadth["down"] or 0
        total = up + down
        br = up / total if total else 0.5
        score += (br - 0.5) * 45
        lu = breadth.get("limit_up") or 0
        ld = breadth.get("limit_down") or 0
        score += (lu - ld) * 0.15
    score = max(3, min(97, score))

    if score >= 62:
        outlook = "看多"
    elif score <= 38:
        outlook = "看空"
    else:
        outlook = "震荡"
    return round(score), outlook


def compute_levels(indices):
    levels = []
    for idx in indices[:1]:  # 以上证为锚
        point = _safe(idx.get("price"))
        if not point:
            continue
        levels.append({
            "name": idx["name"], "close": point,
            "support": round(point * 0.985, 2),
            "resistance": round(point * 1.015, 2),
        })
    return levels


def compute_advice(score, outlook, sectors, breadth):
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
        rec = ["防御性板块（公用事业/医药）", "高股息红利"]
    if sectors:
        rec = [s["name"] for s in sectors[:3]] + rec
    if not rec:
        rec = ["等待方向明朗"]
    return position, strategy, risk, rec


def generate_report(market_data: dict, output_path: str = None) -> str:
    target_date = market_data["target_date"]
    generated_at = market_data["generated_at"]
    d = market_data["data"]

    indices = d.get("indices") or []
    breadth = d.get("breadth")
    sectors = d.get("sectors") or []
    inflow = d.get("main_inflow_stocks") or []
    limitup = d.get("limitup_stocks") or []
    em_ok = d.get("em_ok", True)

    weekend_note = ""
    if not market_data.get("is_trading_day"):
        weekend_note = '<span class="holiday-badge">非交易日</span>'

    degrade_note = ""
    if not em_ok:
        degrade_note = (
            '<div class="alert-box alert-warning">'
            '⚠️ 涨跌家数 / 板块 / 资金数据暂时获取失败（行情源连接异常），'
            '以下仅展示指数实时数据。明日将自动重试。</div>'
        )

    score, outlook = compute_outlook(indices, breadth)
    levels = compute_levels(indices)
    position, strategy, risk_level, rec_dirs = compute_advice(score, outlook, sectors, breadth)

    market_table = _build_index_table(indices)
    index_cards = _build_index_cards(indices)
    index_bar = _build_index_bar(indices)

    sentiment, ratio_class, weekly_stage = _classify_sentiment(breadth)
    up_down_ratio, limit_stats = _format_breadth(breadth)
    breadth_bar = _build_breadth_bar(breadth)

    gauge_svg, gauge_color_class = _build_gauge(score, outlook)
    sector_section = _build_sector_chart(sectors)
    fund_section = _build_fund_section(inflow, limitup)
    advice_section = _build_advice(position, strategy, risk_level, rec_dirs, outlook)
    forecast_section = _build_forecast(score, outlook, levels)
    analysis_section = _build_analysis(indices, breadth, sectors, outlook)

    html = REPORT_TEMPLATE.format(
        report_date=target_date,
        generated_at=generated_at,
        target_date=target_date,
        weekend_note=weekend_note,
        degrade_note=degrade_note,
        market_table=market_table,
        index_cards=index_cards,
        index_bar=index_bar,
        gauge_svg=gauge_svg,
        gauge_score=int(score),
        gauge_color_class=gauge_color_class,
        sentiment=sentiment,
        ratio_class=ratio_class,
        up_down_ratio=up_down_ratio,
        limit_stats=limit_stats,
        weekly_stage=weekly_stage,
        breadth_bar=breadth_bar,
        sector_section=sector_section,
        fund_section=fund_section,
        advice_section=advice_section,
        forecast_section=forecast_section,
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
    if not indices:
        return ""
    rows = ""
    max_abs = max(abs(i.get("change_pct") or 0) for i in indices) or 1
    for idx in indices:
        change = idx.get("change_pct") or 0
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


def _build_index_table(indices: list) -> str:
    if not indices:
        return '<div class="alert-box alert-info">暂无指数数据，请检查数据来源。</div>'
    rows = ""
    for idx in indices:
        change = idx.get("change_pct")
        cls = "neutral"
        arrow = ""
        if change is not None:
            if change > 0:
                cls = "up"; arrow = "↑"
            elif change < 0:
                cls = "down"; arrow = "↓"
        rows += f"""
        <tr>
            <td><strong>{idx['name']}</strong></td>
            <td>{idx.get('price', '--')}</td>
            <td class="{cls}">{change if change is None else f"{change:+.2f}%"} {arrow}</td>
        </tr>
        """
    return f"""
    <table>
        <thead><tr><th>指数</th><th>点位</th><th>涨跌幅</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """


def _build_index_cards(indices: list) -> str:
    if not indices:
        return "<p class='mini-note'>暂无详细指数数据</p>"
    cards = ""
    for idx in indices[:3]:
        change = idx.get("change_pct")
        cls = "neutral"
        if change is not None:
            cls = "up" if change > 0 else "down" if change < 0 else "neutral"
        cards += f"""
        <div class="summary-item" style="margin-bottom:10px;">
            <div class="label">{idx['name']}</div>
            <div class="value">{idx.get('price', '--')}</div>
            <div class="{cls}" style="font-size:14px;margin-top:4px;">{change if change is None else f"{change:+.2f}%"}</div>
        </div>
        """
    return f'<div class="summary-grid">{cards}</div>'


def _classify_sentiment(breadth: dict):
    if not breadth or not breadth.get("total"):
        return '<span class="tag tag-neutral">数据缺失</span>', "neutral", "观察中"
    up = breadth["up"] or 0
    down = breadth["down"] or 0
    total = up + down
    if total > 0 and up / total > 0.65:
        return '<span class="tag tag-bullish">偏多</span>', "up", "<strong style='color:#dc2626;'>修复</strong>"
    elif total > 0 and down / total > 0.55:
        return '<span class="tag tag-bearish">偏空</span>', "down", "<strong style='color:#16a34a;'>调整</strong>"
    return '<span class="tag tag-neutral">震荡</span>', "neutral", "<strong>观察中</strong>"


def _format_breadth(breadth: dict):
    if not breadth:
        return "--", "-- / --"
    up = breadth.get("up")
    down = breadth.get("down")
    limit_up = breadth.get("limit_up")
    limit_down = breadth.get("limit_down")
    ratio = f"{up}:{down}" if up is not None and down is not None else "--"
    limits = f"{limit_up if limit_up is not None else '--'} / {limit_down if limit_down is not None else '--'}"
    return ratio, limits


def _build_breadth_bar(breadth: dict) -> str:
    if not breadth:
        return ""
    up = breadth.get("up") or 0
    down = breadth.get("down") or 0
    total = up + down
    if total == 0:
        return ""
    up_pct = round(up / total * 100, 1)
    down_pct = round(down / total * 100, 1)
    return f"""
    <div class="mini-note" style="margin-top:14px;">涨跌家数分布（总 {breadth.get('total', total)} 家）</div>
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
        return '<p class="mini-note">暂未获取到板块数据</p>'
    rows = ""
    max_change = max(abs(s["change_pct"]) for s in sectors) or 1
    for s in sectors:
        pct = abs(s["change_pct"]) / max_change * 100
        cls = "up" if s["change_pct"] > 0 else "down"
        bar_cls = "bar-up" if s["change_pct"] > 0 else "bar-down"
        inflow = s.get("main_inflow")
        inflow_txt = f" | 主力 {inflow:+.1f}亿" if isinstance(inflow, (int, float)) and inflow != 0 else ""
        rows += f"""
        <div class="sector-row">
            <span class="sector-name">{s['name']}</span>
            <div class="sector-bar-wrap">
                <div class="bar-container" style="margin:0;">
                    <div class="bar {bar_cls}" style="width:{pct:.1f}%;"></div>
                </div>
            </div>
            <span class="sector-change {cls}">{s['change_pct']:+.2f}%{inflow_txt}</span>
        </div>
        """
    return f'<div class="sector-list">{rows}</div>'


def _build_fund_section(inflow: list, limitup: list) -> str:
    parts = []
    if inflow:
        rows = ""
        for x in inflow[:10]:
            cls = "up" if x.get("change_pct", 0) >= 0 else "down"
            rows += f"""
            <tr>
                <td>{x['name']}</td>
                <td class="{cls}">{x.get('change_pct', 0):+.2f}%</td>
                <td class="up">{x.get('main_inflow', 0):+.1f}亿</td>
            </tr>
            """
        parts.append(f"""
        <div class="mini-note">主力资金净流入 TOP10（单位：亿元）</div>
        <table>
            <thead><tr><th>个股</th><th>涨跌幅</th><th>主力净流入</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """)
    else:
        parts.append('<p class="mini-note">主力资金数据暂缺</p>')

    if limitup:
        chips = "".join(f'<span class="chip">{x["name"]} {x.get("change_pct",0):+.2f}%</span>' for x in limitup[:12])
        parts.append(f'<div class="mini-note" style="margin-top:14px;">涨停个股（{len(limitup)} 只，取前 12）</div><div style="margin-top:6px;">{chips}</div>')
    return "".join(parts)


def _build_advice(position, strategy, risk_level, rec_dirs, outlook):
    chips = "".join(f'<span class="chip">{dd}</span>' for dd in rec_dirs)
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
    <div class="advice-strategy"><strong>操作策略：</strong>{strategy}</div>
    <div class="advice-dir"><strong>关注方向：</strong><br>{chips}</div>
    <div class="alert-box alert-warning">
        <strong>风控提示：</strong>以上为 AI 基于当日真实数据的量化建议，仅供参考，<strong>不构成投资建议</strong>。请结合自身风险承受能力独立决策。
    </div>
    """


def _build_forecast(score, outlook, levels):
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
        <span class="mini-note">情绪评分 {int(score)}/100</span>
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
    <div class="disclaimer">注：情景区间为模型基于动量、广度综合推断，关键位按 ±1.5% 估算，实际走势受消息面与资金面影响，仅供参考。</div>
    """


def _build_analysis(indices, breadth, sectors, outlook):
    notes = []
    if breadth and breadth.get("total"):
        up = breadth["up"] or 0
        down = breadth["down"] or 0
        total = up + down
        if total > 0 and up / total > 0.65:
            notes.append("市场涨多跌少，情绪偏多，但连续大涨后注意分化回落。")
        elif total > 0 and down / total > 0.55:
            notes.append("市场跌多涨少，情绪偏空，宜控仓观察，等待超跌反弹信号。")
        else:
            notes.append("涨跌家数分化不大，市场以震荡为主，适合观望。")
    else:
        notes.append("涨跌家数数据暂缺，仅依据指数判断。")

    if sectors:
        top = sectors[0]
        notes.append(f"领涨方向：<strong>{top['name']}</strong>（{top['change_pct']:+.2f}%），关注其持续性。")

    if indices:
        changes = [i.get("change_pct") for i in indices if _safe(i.get("change_pct")) is not None]
        if changes:
            avg = sum(changes) / len(changes)
            if avg > 1:
                notes.append("主要指数收盘偏强，短线可适度参与。")
            elif avg < -1:
                notes.append("主要指数收盘较弱，宜保持轻仓。")

    note_html = "<br>".join(notes) if notes else "未能生成有效研判，请结合实时行情判断。"
    return f"""
    <div class="section"><p>{note_html}</p></div>
    <div class="alert-box alert-warning">
        <strong>风控提示：</strong>本报告为 AI 自动化生成，仅供参考，不构成投资建议。每日 12:10 自动更新。
    </div>
    """


def generate_email_summary(market_data: dict) -> str:
    target_date = market_data["target_date"]
    generated_at = market_data["generated_at"]
    d = market_data["data"]
    indices = d.get("indices") or []
    breadth = d.get("breadth")
    sectors = d.get("sectors") or []

    idx_summary = "\n".join(
        f"{i['name']}: {i.get('price', '--')} ({i['change_pct']:+.2f}%)" if _safe(i.get("change_pct")) is not None else f"{i['name']}: {i.get('price', '--')}"
        for i in indices[:3]
    )
    up = breadth.get("up", "--") if breadth else "--"
    down = breadth.get("down", "--") if breadth else "--"
    top_sector = sectors[0]["name"] if sectors else "—"

    score, outlook = compute_outlook(indices, breadth)
    return f"""A股行情日报 - {target_date}
生成时间: {generated_at}

[主要指数]
{idx_summary}

[市场广度] 涨跌比: {up}:{down}
[领涨板块] {top_sector}
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
            "target_date": "2026-08-08",
            "generated_at": "2026-08-08 12:10",
            "is_trading_day": True,
            "data": {
                "indices": [
                    {"name": "上证指数", "code": "sh000001", "price": 3940.04, "change_abs": 39.69, "change_pct": 1.02},
                    {"name": "深证成指", "code": "sz399001", "price": 14311.01, "change_abs": 200.89, "change_pct": 1.42},
                    {"name": "创业板指", "code": "sz399006", "price": 3563.12, "change_abs": 47.56, "change_pct": 1.35},
                    {"name": "沪深300", "code": "sh000300", "price": 4694.44, "change_abs": 43.13, "change_pct": 0.93},
                    {"name": "科创50", "code": "sh000688", "price": 1744.02, "change_abs": 42.73, "change_pct": 2.51},
                ],
                "breadth": {"up": 3200, "down": 1800, "flat": 200, "limit_up": 65, "limit_down": 3, "total": 5200},
                "sectors": [
                    {"name": "半导体", "change_pct": 4.21, "main_inflow": 58.3},
                    {"name": "计算机", "change_pct": 3.55, "main_inflow": 41.2},
                    {"name": "通信设备", "change_pct": 2.88, "main_inflow": 22.7},
                ],
                "main_inflow_stocks": [
                    {"name": "中芯国际", "code": "688981", "change_pct": 9.91, "main_inflow": 23.5},
                    {"name": "宁德时代", "code": "300750", "change_pct": 3.2, "main_inflow": 18.1},
                ],
                "limitup_stocks": [
                    {"name": "中芯国际", "code": "688981", "change_pct": 9.91},
                    {"name": "比亚迪", "code": "002594", "change_pct": 10.0},
                ],
                "em_ok": True,
                "em_error": "",
            },
        }
    output = sys.argv[2] if len(sys.argv) > 2 else "report.html"
    generate_report(data, output)
    print(f"[OK] 报告已生成: {output}")
