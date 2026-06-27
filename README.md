# 定投周报 — 设计思路

## 项目定位

一个极简的 ETF 定投分析工具。每周自动抓取行情数据，用 AI 分析后生成报告，发布到网页。

**网页地址：** https://sptstim12.github.io/weekly-report/

## 为什么独立出来？

原本是 Stock-Analysis 项目的子模块，依赖原项目的 AI 分析代码。但原项目太复杂（15000+ 行），每次运行需要完整安装所有依赖。

独立出来后的好处：
- **轻量** — 只有 3 个依赖（akshare、openai、pyyaml）
- **自包含** — 不依赖任何外部项目代码
- **易理解** — 全部代码约 400 行，一个文件搞定
- **易维护** — 改配置、换模型都很简单

## 数据流

```
config.yaml          ← 你配置的股票列表 + AI 设置
    │
    ▼
akshare              ← 公开数据源，免费，无需 API Key
    │                 抓取: ETF 历史K线（fund_etf_hist_em）
    │                 计算: 最新价、涨跌幅、MA5/MA10/MA20
    ▼
DeepSeek API         ← AI 分析（通过 OpenAI 兼容接口）
    │                 输入: 行情数据 + 分析提示词
    │                 输出: JSON（评分、趋势、建议、详细分析）
    ▼
output/
  ├── index.html     ← 网页版报告（部署到 GitHub Pages）
  └── report_*.md    ← Markdown 版报告（留存备查）
```

## 为什么选 akshare？

- 免费，无需注册
- 覆盖 A 股全部 ETF
- 数据还算及时
- ETF 数据用 `fund_etf_hist_em` 接口，普通股票用 `stock_zh_a_hist`

## 为什么用 DeepSeek？

- 便宜（100 万 token 约 1 元）
- 分析质量不错
- 中文友好

如果以后想换，改 config.yaml 里的 base_url 和 model 就行。

## 项目结构

```
weekly-report/
├── weekly_report.py              # 核心脚本（一个文件搞定）
├── config.yaml                   # 股票列表 + AI 配置
├── requirements.txt              # 依赖包（3个）
├── .env.example                  # API Key 模板（不含真实Key）
├── .env                          # 本地API Key（不提交到Git）
├── SKILL.md                      # AI 协作技能文件
├── README.md                     # 本文件
├── output/                       # 报告输出（本地）
│   ├── index.html
│   └── report_*.md
└── .github/workflows/
    └── weekly-report.yml         # 周二 12:00 自动运行 + 部署
```

## 部署方式

通过 GitHub Actions 每周二中午 12:00（北京时间）自动运行：

1. 启动 Ubuntu 虚拟机
2. 安装 Python + 依赖
3. 运行 `python weekly_report.py`
4. 将 `output/` 部署到 `gh-pages` 分支
5. GitHub Pages 自动更新网页

也可以本地运行：
```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 API Key
python weekly_report.py
```

## 如何扩展？

- 加股票 → 改 `config.yaml` 的 `stocks` 列表
- 改分析维度 → 改 `build_analysis_prompt()` 函数里的提示词
- 换 AI 模型 → 改 `config.yaml` 的 `ai` 部分
- 改数据源 → 改 `fetch_stock_data()` 函数
- 改运行频率 → 改 `.github/workflows/weekly-report.yml` 的 cron 表达式
- 加通知推送 → 在 `main()` 结束时加推送逻辑

## 当前配置

| 项目 | 配置 |
|------|------|
| GitHub 仓库 | https://github.com/sptstim12/weekly-report |
| 网页地址 | https://sptstim12.github.io/weekly-report/ |
| AI 模型 | DeepSeek (deepseek-chat) |
| 数据源 | akshare (fund_etf_hist_em) |
| 定投标的 | 510310 沪深300ETF、588000 科创50ETF、515080 新能源ETF、563220 新基建ETF、510500 中证500ETF |
| 定时运行 | 每周二 UTC 04:00（北京时间 12:00） |
| 部署方式 | GitHub Actions → gh-pages → GitHub Pages |
