---
name: "weekly_report"
description: "定投周报生成器。独立运行的 ETF 定投分析工具，抓取行情数据并通过 AI 生成分析报告。当用户想要分析定投组合、生成周报、或配置自动推送时调用。"
---

# 定投周报生成器（独立版）

独立的 ETF 定投分析工具，不依赖 Stock-Analysis 项目。

## 核心能力

1. **行情数据抓取** — 通过 akshare 获取 ETF 历史 K 线、实时行情
2. **AI 分析** — 调用 DeepSeek API（或任何 OpenAI 兼容接口）分析定投价值
3. **报告生成** — 输出 Markdown 报告 + HTML 网页

## 使用方式

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key（三选一）
# 方式1: 环境变量
export DEEPSEEK_API_KEY=sk-xxx

# 方式2: .env 文件
cp .env.example .env
# 编辑 .env 填入 Key

# 方式3: config.yaml
# 在 ai.api_key 直接写 Key

# 运行
python weekly_report.py

# 预览（不保存文件）
python weekly_report.py --dry-run

# 临时指定股票
python weekly_report.py --stocks 510310,588000
```

## 配置说明

所有配置在 `config.yaml`：

- `stocks` — 定投基金列表
- `ai.provider` — AI 供应商名（显示用）
- `ai.base_url` — API 地址
- `ai.model` — 模型名
- `ai.api_key_env` — 从哪个环境变量读 Key

## 切换 AI 模型

在 `config.yaml` 修改 `ai` 部分，例如：

```yaml
# 切换到 OpenAI
ai:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"
  api_key_env: "OPENAI_API_KEY"
```

同时确保对应的 API Key 已配置。

## 输出结构

```
output/
├── index.html           # 最新报告（网页）
├── report_20260701.md   # 历史报告（Markdown）
└── report_20260624.md
```
