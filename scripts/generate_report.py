"""
HTML 报告生成模块
基于市场数据生成完整的A股行情研判报告
"""
import json
import os
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
h1 {{ font-size: 20px; font-weight: 600; margin-bottom: 4px; }}
h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #555; }}
.subtitle {{ font-size: 13px; color: #999; margin-bottom: 16px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 8px 10px; text-align: center; border-bottom: 1px solid #eee; }}
th {{ background: #f8f9fa; font-weight: 500; color: #666; font-size: 12px; }}
.up {{ color: #dc2626; font-weight: 600; }}
.down {{ color: #16a34a; font-weight: 600; }}
.tag {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    margin-right: 6px;
}}
.tag-bullish {{ background: #fef2f2; color: #dc2626; }}
.tag-bearish {{ background: #f0fdf4; color: #16a34a; }}
.tag-neutral {{ background: #f5f5f5; color: #888; }}
.bar-container {{ height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; margin: 8px 0; }}
.bar {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
.bar-up {{ background: #dc2626; }}
.bar-down {{ background: #16a34a; }}
.summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;
}}
.summary-item {{
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
}}
.summary-item .label {{ font-size: 12px; color: #999; margin-bottom: 4px; }}
.summary-item .value {{ font-size: 18px; font-weight: 600; }}
.alert-box {{
    padding: 12px 16px;
    border-radius: 8px;
    margin-top: 12px;
    font-size: 13px;
    line-height: 1.6;
}}
.alert-warning {{ background: #fef9e7; border-left: 3px solid #f0ad4e; color: #856404; }}
.alert-info {{ background: #e8f4fd; border-left: 3px solid #378add; color: #0c447c; }}
.alert-danger {{ background: #fef2f2; border-left: 3px solid #dc2626; color: #991b1b; }}
.section {{ margin-top: 8px; }}
.section p {{ font-size: 13px; margin-bottom: 8px; }}
.footer {{
    text-align: center;
    font-size: 11px;
    color: #bbb;
    margin-top: 20px;
    padding: 10px 0;
}}
hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
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
    <div class="summary-grid">
        <div class="summary-item">
            <div class="label">涨跌比</div>
            <div class="value">{up_down_ratio}</div>
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
</div>

<div class="card">
    <h2>行业板块</h2>
    {sector_section}
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
    本报告由 AI 自动生成，仅供参考，不构成投资建议 | {generated_at}
</div>
</body>
</html>"""


def generate_report(market_data: dict, output_path: str = None) -> str:
    """
    生成 HTML 报告
    market_data: fetch_all_market_data 返回的数据结构
    output_path: 输出路径（可选）
    返回: HTML 字符串
    """
    target_date = market_data["target_date"]
    generated_at = market_data["generated_at"]
    data = market_data["data"]

    # 检查是否为交易日（简单判断：如果有行情数据就是交易日）
    overview_text = data.get("market_overview", {}).get("text", "")
    is_trading_day = len(overview_text) > 50 and "行情" not in overview_text[:20].lower()

    weekend_note = ""
    today = datetime.now()
    if today.weekday() >= 5:  # 周末
        weekend_note = f" <span class='tag tag-neutral'>今日休市</span>"

    # 构建各模块
    market_table = _build_market_table(data)
    sentiment_section = _build_sentiment(data, overview_text)
    sector_section = _build_sector(data)
    news_section = _build_news(data)
    analysis_section = _build_analysis(data, market_table)

    # 提取关键数据
    sentiment_text, up_down_ratio, limit_stats, weekly_stage = _extract_summary(
        data, overview_text
    )

    html = REPORT_TEMPLATE.format(
        report_date=target_date,
        generated_at=generated_at,
        target_date=target_date,
        weekend_note=weekend_note,
        market_table=market_table,
        sentiment_section=sentiment_section,
        sentiment=sentiment_text,
        up_down_ratio=up_down_ratio,
        limit_stats=limit_stats,
        weekly_stage=weekly_stage,
        sector_section=sector_section,
        news_section=news_section,
        analysis_section=analysis_section,
    )

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[INFO] 报告已保存: {output_path}")

    return html


def _build_market_table(data: dict) -> str:
    overview = data.get("market_overview", {}).get("text", "")
    fund = data.get("fund_flow", {}).get("text", "")

    # 尝试提取指数数据（简化版，实际应解析 structured data）
    combined = overview + "\n" + fund

    return f"""
    <p style="font-size:13px;color:#666;margin-bottom:12px;">以下基于上一交易日市场数据汇总：</p>
    <div class="alert-box alert-info">
        {_truncate(overview, 500) or "正在获取行情数据..."}
    </div>
    """


def _build_sentiment(data: dict, overview: str) -> str:
    text = overview[:300] if overview else "等待数据..."
    return f'<div class="section"><p>{text}</p></div>'


def _build_sector(data: dict) -> str:
    sector = data.get("sector_ranking", {}).get("text", "")
    text = sector[:400] if sector else "等待数据..."
    return f'<div class="section"><p>{text}</p></div>'


def _build_news(data: dict) -> str:
    news = data.get("news", {}).get("text", "")
    fund = data.get("fund_flow", {}).get("text", "")
    combined = (news + "\n" + fund)[:500]
    return f'<div class="section"><p>{combined or "等待数据..."}</p></div>'


def _build_analysis(data: dict, market_table: str) -> str:
    return f"""
    <div class="section">
        <p>综合以上数据，AI 研判如下：</p>
    </div>
    <div class="alert-box alert-warning">
        本报告为自动化生成，详细版请参考桌面端 WorkBuddy 生成的完整分析报告。<br>
        每日 12:10 自动更新。
    </div>
    """


def _extract_summary(data: dict, overview: str):
    """从数据中提取摘要信息"""
    sentiment = "等待数据"
    ratio = "--"
    limits = "--"
    stage = "观察中"

    # 简化版摘要
    if "反弹" in overview or "涨" in overview:
        sentiment = '<span class="tag tag-bullish">修复</span>'
    elif "跌" in overview:
        sentiment = '<span class="tag tag-bearish">偏弱</span>'
    else:
        sentiment = '<span class="tag tag-neutral">震荡</span>'

    return sentiment, ratio, limits, stage


def _truncate(text: str, max_len: int = 500) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def generate_email_summary(market_data: dict) -> str:
    """生成邮件正文摘要"""
    target_date = market_data["target_date"]
    generated_at = market_data["generated_at"]
    overview = market_data["data"].get("market_overview", {}).get("text", "")

    # 截取关键信息
    preview = _truncate(overview, 200)

    return f"""A股行情日报 - {target_date}
生成时间: {generated_at}

[市场速览]
{preview}

完整报告请点击链接查看。

---
本报告由 AI 自动生成，仅供参考，不构成投资建议。
"""


if __name__ == "__main__":
    # 测试：从 JSON 文件加载数据
    import sys

    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # 创建测试数据
        data = {
            "target_date": "2026-07-31",
            "generated_at": "2026-08-01",
            "data": {
                "market_overview": {"text": "测试数据：上证指数收涨，两市成交活跃。"},
                "sector_ranking": {"text": "测试数据：新能源板块领涨。"},
                "fund_flow": {"text": "测试数据：北向资金净流入。"},
                "news": {"text": "测试数据：无重大新闻。"},
            },
        }

    output = sys.argv[2] if len(sys.argv) > 2 else "report.html"
    generate_report(data, output)
    print(f"[OK] 报告已生成: {output}")
