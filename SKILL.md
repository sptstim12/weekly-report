---
name: "weekly_report"
description: "定投周报生成器。独立运行的 ETF 定投分析工具，通过 akshare 抓取行情、DeepSeek API 生成分析，输出 Markdown + HTML 报告。"
---

# 定投周报生成器

## 核心流程

1. 读取 `config.yaml` → 获取股票列表和 AI 配置
2. 通过 `akshare.fund_etf_hist_em()` 抓取 ETF K 线数据
3. 构建分析提示词 → 调用 DeepSeek API（OpenAI 兼容接口）
4. 生成 Markdown 报告 + HTML 网页 → 保存到 `output/`

## 关键函数

| 函数 | 作用 |
|------|------|
| `fetch_stock_data(code)` | 抓取单只 ETF 的 K 线、均线、最新价 |
| `build_analysis_prompt(data)` | 构建发送给 AI 的分析提示词 |
| `call_ai(client, model, prompt)` | 调用 AI，返回 JSON 分析结果 |
| `generate_markdown(results, time)` | 生成 Markdown 报告 |
| `generate_html(results, time)` | 生成 HTML 网页 |

## 配置入口

`config.yaml` — 控制所有行为：
- `stocks` — 定投标的列表
- `ai` — 模型配置（provider / base_url / model / api_key_env）
- `report.keep_history` — 保留历史报告数量

## AI 模型切换

修改 `config.yaml` 的 `ai` 段即可，支持任何 OpenAI 兼容接口：

```yaml
ai:
  provider: "deepseek"          # 显示名称
  base_url: "https://api.deepseek.com"  # API 地址
  model: "deepseek-chat"        # 模型名
  api_key_env: "DEEPSEEK_API_KEY"  # 从哪个环境变量读 Key
```

## 输出结构

```
output/
├── index.html           # 最新报告（部署到 GitHub Pages）
└── report_YYYYMMDD.md   # 历史 Markdown 报告
```
