# 定投周报 — 设计思路

## 项目定位

一个极简的 ETF 定投分析工具。每周自动抓取行情数据，用 AI 分析后生成报告，发布到网页。

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
    │                 抓取: 历史K线、实时价格、均线
    ▼
DeepSeek API         ← AI 分析（通过 OpenAI 兼容接口）
    │                 输入: 行情数据 + 分析提示词
    │                 输出: JSON（评分、趋势、建议、详细分析）
    ▼
output/
  ├── index.html     ← 网页版报告（直接浏览器打开）
  └── report_*.md    ← Markdown 版报告（留存备查）
```

## 为什么选 akshare？

- 免费，无需注册
- 覆盖 A 股全部 ETF
- 数据还算及时（延迟约 15 分钟）

## 为什么用 DeepSeek？

- 便宜（100 万 token 约 1 元）
- 分析质量不错
- 中文友好

如果以后想换，改 config.yaml 里的 base_url 和 model 就行。

## 部署方式

当前通过 GitHub Actions 每周二自动运行。工作流在 Stock-Analysis 仓库的 `.github/workflows/weekly-report.yml`。

也可以：
- 在自己的电脑上定时运行（Windows 任务计划器）
- 部署到云服务器（crontab 定时任务）

## 如何扩展？

- 加股票 → 改 config.yaml
- 改分析维度 → 改 build_analysis_prompt() 函数里的提示词
- 换数据源 → 改 fetch_stock_data() 函数
- 加通知推送 → 在 main() 结束时加推送逻辑（微信、邮件等）
