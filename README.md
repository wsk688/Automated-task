# A股行情日报 — 云端自动化

每天中午 12:10 自动拉取 A 股行情数据，生成分析报告，**发邮件到你的手机**。关机也能跑。

## 工作原理

```
GitHub Actions（云端）每天 12:10 触发
  ↓
拉取真实行情（腾讯财经指数 + 东方财富涨跌家数/板块/资金）
  ↓
生成 HTML 分析报告
  ↓
发邮件到 QQ 邮箱（含摘要 + 在线链接）
  ↓
报告部署到 GitHub Pages（手机浏览器可查看）
```

> **数据源说明**：
> - 指数（上证 / 深证 / 创业板 / 沪深300 / 科创50）：腾讯财经 `qt.gtimg.cn` 实时接口（免 token，云端稳定）
> - 涨跌家数 / 涨停跌停 / 行业板块排行 / 主力资金流入个股：**Tushare 专业 API**（需免费 token `TUSHARE_TOKEN`，云端稳定可靠）
> - 若未配置 Tushare token：自动降级到东方财富 `push2` 公开接口（云端美国 IP 可能取不到，章节会留空）
> - 任一行情源短时不可用时指数仍来自腾讯，不会因单点故障导致任务完全失败。

## 三步部署

### 第一步：创建 GitHub 仓库

1. 访问 https://github.com/new
2. 仓库名填 `market-daily`（或你喜欢的名字）
3. 设为 **Private**（推荐，数据不公开）
4. 不要勾选任何初始化选项
5. 点击 **Create repository**

### 第二步：推送代码

在终端中执行（替换 `你的用户名` 为你的 GitHub 用户名）：

```bash
# 进入项目目录
cd "D:\体重健康管理\2026-08-01-12-27-14\market-cloud-auto"

# 初始化 Git
git init
git checkout -b main

# 添加所有文件
git add .

# 提交
git commit -m "初始化 A股行情日报 云端自动化"

# 关联远程仓库
git remote add origin https://github.com/你的用户名/market-daily.git

# 推送
git push -u origin main
```

### 第三步：配置 Secrets

在 GitHub 仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

添加以下 Secrets：

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `TUSHARE_TOKEN` | ⚠️ 见下方 | **Tushare API token（涨跌家数/板块/资金的核心数据源，云端稳定）** |
| `QQ_EMAIL` | `1876636858@qq.com` | 发件 QQ 邮箱 |
| `QQ_EMAIL_AUTH` | ⚠️ 见下方 | QQ 邮箱 SMTP 授权码 |
| `TO_EMAIL` | `1876636858@qq.com` | 收件邮箱 |

> **为什么需要 Tushare？** 本项目指数用腾讯接口（免 token），但涨跌家数 / 行业板块 / 主力资金这几项，东方财富接口在 GitHub 云端（美国 IP）取不到数据。Tushare 是专业 A股数据 API，云端稳定可靠，免费注册即可用。未配置 TUSHARE_TOKEN 时，程序会自动降级尝试东方财富（可能为空）。

#### 如何获取 Tushare token（免费，约 3 分钟）

1. 打开 https://tushare.pro/register 注册（手机号验证）
2. 登录后进入 **个人主页 → 接口TOKEN** 复制你的 token
3. 把 token 填到 `TUSHARE_TOKEN`
4. （可选）在「用户中心 → 积分管理」做任务攒积分，确保 `daily` / `index_daily` / `moneyflow` 等接口可用（基础接口免费）

#### 如何获取 QQ 邮箱授权码

1. 登录 QQ 邮箱网页版 → **设置 → 账户**
2. 找到 **POP3/IMAP/SMTP 服务**
3. 开启 **SMTP 服务**
4. 按提示发送短信获取**授权码**（16位字符，不是 QQ 密码）
5. 把授权码填到 `QQ_EMAIL_AUTH`

### 启用 GitHub Pages

1. 仓库页 **Settings → Pages**
2. Source 选 **Deploy from a branch**
3. Branch 选 **gh-pages** → **/(root)** → Save
4. 等待 1-2 分钟后，报告会出现在：`https://你的用户名.github.io/market-daily/reports/`

### 📱 手机端每天接收推送（两种方式互补）

本项目的"推送到手机"由**邮件步骤**完成，Pages 负责"随时打开看"，二者配合即可：

**方式一：QQ 邮箱 APP 每日推送（推荐，主动提醒）**
1. 手机应用商店安装 **QQ 邮箱** APP，登录上面的 `TO_EMAIL` 邮箱
2. 工作流每天 12:10（工作日）跑完后，会自动发来一封邮件：
   - 邮件正文：当日行情**摘要 + 「查看完整报告」按钮**
   - 邮件附件：完整 HTML 报告（可直接在手机浏览器打开）
3. 手机收到邮件即收到推送提醒，点「查看完整报告」即跳转到 Pages 在线完整报告

**方式二：GitHub Pages 随时看（无需推送，自己打开）**
- 浏览器（含手机）访问 `https://你的用户名.github.io/Automated-task/reports/`
- 每天报告以 `daily_YYYY-MM-DD.html` 命名，自动更新，离线缓存后可反复看

> **容错说明**：若未配置 QQ 邮箱三个 Secrets，邮件步骤会自动跳过并提示，但 **Pages 仍会正常部署**，手机仍可访问在线报告，不会因缺少邮箱配置而中断整个任务。

### 最后：开启 Workflow 权限

1. **Settings → Actions → General**
2. Workflow permissions 选 **Read and write permissions**
3. 勾选 **Allow GitHub Actions to create and approve pull requests**
4. Save

## 验证

1. 在仓库页点击 **Actions** 标签
2. 找到「A股行情日报」workflow
3. 点击 **Run workflow** → 选择 main 分支 → **Run workflow**
4. 等 1-2 分钟，检查 QQ 邮箱是否收到邮件

## 定时规则

- 每天 **12:10** 执行（仅工作日）
- 周末和节假日跳过，周一分析上周五数据
- 可在 `.github/workflows/daily.yml` 中修改 cron 表达式（默认 `10 4 * * 1-5`，即北京时间工作日 12:10）

## 文件说明

```
market-cloud-auto/
├── .github/workflows/daily.yml   # 定时任务配置
├── scripts/
│   ├── fetch_data.py            # 行情数据拉取
│   ├── generate_report.py       # HTML 报告生成
│   └── send_email.py            # QQ 邮箱发送
├── reports/                     # 生成的报告（自动创建）
└── requirements.txt
```
