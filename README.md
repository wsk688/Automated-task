# A股行情日报 — 云端自动化

每天中午 12:10 自动拉取 A 股行情数据，生成分析报告，**发邮件到你的手机**。关机也能跑。

## 工作原理

```
GitHub Actions（云端）每天 12:10 触发
  ↓
拉取 NeoData 行情数据
  ↓
生成 HTML 分析报告
  ↓
发邮件到 QQ 邮箱（含摘要 + 在线链接）
  ↓
报告部署到 GitHub Pages（手机浏览器可查看）
```

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

添加以下 4 个 Secrets：

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `NEODATA_TOKEN` | `tk_9vRRzRpjcvLHrH62jlGNEsVv3uAj2zxr` | NeoData API 密钥 |
| `QQ_EMAIL` | `1876636858@qq.com` | 发件 QQ 邮箱 |
| `QQ_EMAIL_AUTH` | ⚠️ 见下方 | QQ 邮箱 SMTP 授权码 |
| `TO_EMAIL` | `1876636858@qq.com` | 收件邮箱 |

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
- 可在 `.github/workflows/daily.yml` 第 6 行修改 cron 表达式

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
