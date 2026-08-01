"""
邮件发送模块
通过 QQ 邮箱 SMTP 发送每日行情报告
"""
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_report_email(
    html_report: str,
    summary: str,
    report_date: str,
    pages_url: str = "",
):
    """
    发送邮件到指定 QQ 邮箱
    """
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    sender_email = os.environ.get("QQ_EMAIL")
    sender_auth = os.environ.get("QQ_EMAIL_AUTH")
    receiver_email = os.environ.get("TO_EMAIL", sender_email)

    if not sender_email or not sender_auth:
        raise RuntimeError("请设置环境变量 QQ_EMAIL 和 QQ_EMAIL_AUTH")

    subject = f"A股行情日报 - {report_date}"

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    # 纯文本版本
    text_content = summary
    if pages_url:
        text_content += f"\n\n在线查看: {pages_url}"

    # HTML 版本（移动端友好）
    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 16px; color: #333; background: #f5f5f5;">
<div style="background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 4px 0; font-size: 18px;">A股行情日报</h2>
    <p style="color: #999; font-size: 12px; margin: 0 0 16px 0;">{report_date} | 自动生成</p>
    <p style="font-size: 14px; line-height: 1.8; white-space: pre-wrap;">{summary}</p>
    {f'<p style="margin-top: 16px;"><a href="{pages_url}" style="display: inline-block; padding: 10px 24px; background: #378add; color: #fff; text-decoration: none; border-radius: 8px; font-size: 14px;">查看完整报告</a></p>' if pages_url else ''}
</div>
<p style="text-align: center; font-size: 11px; color: #bbb; margin-top: 16px;">
    本报告由 AI 自动生成，仅供参考，不构成投资建议
</p>
<div style="text-align: center; font-size: 11px; color: #ccc; margin-top: 8px;">
    Powered by WorkBuddy GitHub Actions
</div>
</body>
</html>"""

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # 添加报告附件
    if html_report:
        attachment = MIMEText(html_report, "html", "utf-8")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"market_report_{report_date}.html",
        )
        msg.attach(attachment)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, sender_auth)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print(f"[OK] 邮件已发送到 {receiver_email}")
        return True

    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")
        return False


if __name__ == "__main__":
    test_summary = "测试邮件：A股行情日报"
    send_report_email(
        html_report="<h1>测试报告</h1>",
        summary=test_summary,
        report_date=datetime.now().strftime("%Y-%m-%d"),
        pages_url="https://example.com",
    )
