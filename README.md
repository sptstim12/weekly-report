# 定投周报 — 设计思路

## 项目定位

一个极简的 ETF 定投分析工具。每周自动抓取行情数据，用 AI 分析后生成报告，发布到网页。

**网页地址：** https://sptstim12.github.io/weekly-report/

## 数据流

```
config.yaml          ← 股票列表 + AI 设置 + 推荐开关
    │
    ▼
akshare              ← 公开数据源，免费，无需 API Key
    │                 抓取: ETF 历史K线（fund_etf_hist_em）
    │                 计算: 最新价、涨跌幅、MA5/MA10/MA20
    │                 推荐: 全市场 ETF 筛选（fund_etf_spot_em）
    ▼
DeepSeek API         ← AI 分析 + AI 推荐（OpenAI 兼容接口）
    │                 分析: 评分、趋势、建议、风险
    │                 推荐: 从候选池精选 3-5 只 ETF
    ▼
output/
  ├── index.html     ← 网页版报告（部署到 GitHub Pages）
  └── report_*.md    ← Markdown 版报告（留存备查）
```

## 核心功能

### 1. 定投分析
- 对 config.yaml 中配置的 ETF 逐一分析
- AI 输出：评分（0-100）、趋势判断、操作建议、风险提示
- 支持临时指定股票：`python weekly_report.py --stocks 510310,588000`

### 2. AI 推荐 ETF（可选，开关控制）
- 从全市场 1500+ 只 ETF 中筛选
- 综合量比、主力资金流向、换手率、涨跌幅等技术指标
- AI 精选 3-5 只短期关注标的，给出推荐理由
- 在 `config.yaml` 中设置 `recommend.enabled: false` 即可关闭

## 为什么用 DeepSeek？

- 便宜（100 万 token 约 1 元）
- 分析质量不错
- 中文友好

如果以后想换，改 `config.yaml` 里的 `base_url` 和 `model` 就行。

## 项目结构

```
weekly-report/
├── weekly_report.py              # 核心脚本（一个文件搞定）
├── config.yaml                   # 股票列表 + AI 配置 + 推荐开关
├── requirements.txt              # 依赖包（3个）
├── .env.example                  # API Key 模板（不含真实Key）
├── .env                          # 本地API Key（不提交到Git）
├── SKILL.md                      # AI 协作技能文件
├── README.md                     # 本文件
├── output/                       # 报告输出（本地）
│   ├── index.html
│   └── report_*.md
└── .github/workflows/
    └── weekly-report.yml         # 自动运行 + 部署
```

## 部署方式

通过 GitHub Actions 自动运行：
- **触发方式**：push 代码、手动触发、每周二 12:00（北京时间）
- 安装依赖 → 运行分析 → 生成报告 → 部署到 gh-pages 分支
- GitHub Pages 自动更新网页

### GitHub 设置清单

| 设置项 | 位置 | 值 |
|--------|------|-----|
| DEEPSEEK_API_KEY | Settings → Secrets → Actions | 你的 API Key |
| Pages Source | Settings → Pages | Deploy from branch / gh-pages / (root) |
| Workflow permissions | Settings → Actions → General | Read and write permissions |

### 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 API Key
python weekly_report.py
```

## 当前配置

| 项目 | 配置 |
|------|------|
| GitHub 仓库 | https://github.com/sptstim12/weekly-report |
| 网页地址 | https://sptstim12.github.io/weekly-report/ |
| AI 模型 | DeepSeek (deepseek-chat) |
| 数据源 | akshare (fund_etf_hist_em / fund_etf_spot_em) |
| 定投标的 | 510310 沪深300ETF、588000 科创50ETF、515080 中证红利ETF、563220 A500富国ETF、510500 中证500南方ETF |
| 推荐功能 | 开启（AI 从全市场推荐 3-5 只 ETF） |
| 定时运行 | 每周二 UTC 04:00（北京时间 12:00）+ push 触发 |
| 时区 | 北京时间 (UTC+8) |

## 如何扩展？

- 加/减股票 → 改 `config.yaml` 的 `stocks` 列表
- 开关推荐 → 改 `config.yaml` 的 `recommend.enabled`
- 换 AI 模型 → 改 `config.yaml` 的 `ai` 部分
- 改分析提示词 → 改 `build_analysis_prompt()` 函数
- 改推荐提示词 → 改 `build_recommend_prompt()` 函数
- 改运行频率 → 改 `.github/workflows/weekly-report.yml` 的 cron
