#!/usr/bin/env python3
"""
定投周报生成器
=======================

功能：
  1. 通过 akshare 抓取 ETF 历史 K 线数据
  2. 调用 DeepSeek API 进行 AI 分析
  3. 生成 Markdown 报告 + HTML 网页

用法：
  python weekly_report.py                  # 正常运行
  python weekly_report.py --dry-run         # 预览模式（不保存文件）
  python weekly_report.py --stocks 510310,588000  # 临时指定股票

AI 模型切换：
  修改 config.yaml 中的 ai.provider 和对应的 api_key_env
  支持 deepseek / openai / gemini（通过 OpenAI 兼容接口）
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")

# ── 依赖检查 ──────────────────────────────────────────
try:
    import yaml
except ImportError:
    print("[错误] 缺少 pyyaml，请运行: pip install pyyaml")
    sys.exit(1)

try:
    import akshare as ak
except ImportError:
    print("[错误] 缺少 akshare，请运行: pip install akshare")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("[错误] 缺少 openai，请运行: pip install openai")
    sys.exit(1)

# ── 路径 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"


# ========================================================
# 1. 配置
# ========================================================

def load_config() -> Dict[str, Any]:
    """读取 config.yaml"""
    path = PROJECT_ROOT / "config.yaml"
    if not path.exists():
        print("[错误] 找不到 config.yaml")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key(config: Dict) -> str:
    """
    获取 API Key，优先级：
    1. 环境变量（如 DEEPSEEK_API_KEY）
    2. config.yaml 中的 api_key 字段
    3. .env 文件
    """
    ai_cfg = config.get("ai", {})
    env_var = ai_cfg.get("api_key_env", "DEEPSEEK_API_KEY")

    # 先看环境变量
    key = os.getenv(env_var, "")
    if key:
        return key

    # 再看 config.yaml 里直接写的
    key = ai_cfg.get("api_key", "")
    if key and key != "你的APIKEY":
        return key

    # 尝试从 .env 文件加载
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == env_var and v.strip():
                    return v.strip()

    print(f"[错误] 未找到 API Key，请设置环境变量 {env_var}")
    print(f"       或编辑 config.yaml 中的 ai.api_key 字段")
    print(f"       或创建 .env 文件: {env_var}=你的Key")
    sys.exit(1)


def get_client(config: Dict) -> OpenAI:
    """根据配置创建 OpenAI 兼容客户端"""
    ai_cfg = config.get("ai", {})

    base_url = ai_cfg.get("base_url", "https://api.deepseek.com")
    api_key = get_api_key(config)

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )


# ========================================================
# 2. 数据抓取（通过 akshare）
# ========================================================

def fetch_stock_data(code: str, days: int = 60) -> Dict[str, Any]:
    """
    抓取股票/ETF 的近期行情数据。

    返回:
        {
            "code": "510310",
            "name": "沪深300ETF",
            "latest_price": 3.850,
            "change_pct": 0.52,
            "kline": [{"date": "2026-06-27", "open": 3.82, ...}, ...],
            "ma5": 3.81,
            "ma10": 3.78,
            "ma20": 3.72,
        }
    """
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days + 10)).strftime("%Y%m%d")

    # ETF 用 fund_etf_hist_em，普通股票用 stock_zh_a_hist
    df = None
    name = code

    # 先尝试 ETF 接口（我们的标的都是 ETF）
    try:
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
    except Exception:
        pass

    # 如果 ETF 接口没数据，尝试股票接口
    if df is None or df.empty:
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
        except Exception as e:
            raise RuntimeError(f"无法获取 {code} 的行情数据: {e}")

    if df is None or df.empty:
        raise RuntimeError(f"{code} 返回空数据")

    # 从 K 线数据中取最新一日作为当前行情
    latest = df.iloc[-1]
    latest_price = float(latest["收盘"])
    change_pct = float(latest.get("涨跌幅", 0)) if "涨跌幅" in df.columns else 0.0

    # 计算均线
    closes = df["收盘"].astype(float)
    ma5 = float(closes.rolling(5).mean().iloc[-1])
    ma10 = float(closes.rolling(10).mean().iloc[-1])
    ma20 = float(closes.rolling(20).mean().iloc[-1])

    # 取最近 N 天的 K 线（精简字段）
    recent = df.tail(days)
    kline = []
    for _, row in recent.iterrows():
        kline.append({
            "date": str(row.get("日期", "")),
            "open": float(row["开盘"]),
            "high": float(row["最高"]),
            "low": float(row["最低"]),
            "close": float(row["收盘"]),
            "volume": int(row.get("成交量", 0)),
        })

    return {
        "code": code,
        "name": name,
        "latest_price": round(latest_price, 3),
        "change_pct": round(change_pct, 2),
        "ma5": round(ma5, 3),
        "ma10": round(ma10, 3),
        "ma20": round(ma20, 3),
        "kline": kline,
    }


# ========================================================
# 3. AI 分析
# ========================================================

def build_analysis_prompt(stock_data: Dict) -> str:
    """根据股票数据构建分析提示词"""
    kline = stock_data["kline"]

    # 最近 5 天摘要
    recent_days = kline[-5:]
    price_summary = "\n".join(
        f"  {d['date']}: 开{d['open']} 高{d['high']} 低{d['low']} 收{d['close']} 量{d['volume']}"
        for d in recent_days
    )

    # 30 天价格范围
    all_closes = [d["close"] for d in kline]
    high_30d = max(all_closes)
    low_30d = min(all_closes)

    prompt = f"""你是一位专业的 ETF 定投分析顾问。请根据以下行情数据，对这只基金进行分析，给出定投建议。

## 基金信息
- 代码：{stock_data['code']}
- 名称：{stock_data['name']}
- 最新价：{stock_data['latest_price']}
- 今日涨跌幅：{stock_data['change_pct']}%
- MA5（5日均线）：{stock_data['ma5']}
- MA10（10日均线）：{stock_data['ma10']}
- MA20（20日均线）：{stock_data['ma20']}
- 30日最高价：{high_30d}
- 30日最低价：{low_30d}

## 最近 5 个交易日行情
{price_summary}

## 均线排列
- 价格相对 MA5：{"上方" if stock_data['latest_price'] > stock_data['ma5'] else "下方"}（偏离 {round(abs(stock_data['latest_price'] - stock_data['ma5']) / stock_data['ma5'] * 100, 1)}%）
- 均线趋势：{"多头排列(MA5>MA10>MA20)" if stock_data['ma5'] > stock_data['ma10'] > stock_data['ma20'] else "非多头排列"}

## 分析要求
请从定投角度出发，给出以下 JSON 格式的分析结果（只返回 JSON，不要其他文字）：

```json
{{
  "score": 75,
  "trend": "震荡偏多",
  "advice": "继续定投",
  "summary": "一句话总结当前情况和定投建议",
  "detail": "2-3句话的详细分析，包括对趋势、均线、成交量的解读",
  "risk": "需要注意的风险点"
}}
```

字段说明：
- score: 0-100 评分，70以上适合定投，50-70可观望，50以下谨慎
- trend: 趋势判断（如"上升趋势""下降趋势""震荡"等）
- advice: 操作建议（"继续定投""建议加仓""建议观望""可适当减仓"）
- summary: 一句话总结
- detail: 详细分析
- risk: 风险提示"""

    return prompt


def call_ai(client: OpenAI, model: str, prompt: str) -> Dict[str, Any]:
    """调用 AI 进行分析"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是一位专业的 ETF 定投分析顾问。你总是以 JSON 格式回复分析结果。"
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    content = response.choices[0].message.content.strip()

    # 清洗：去掉可能的 markdown 代码块标记
    if content.startswith("```"):
        lines = content.split("\n")
        # 去掉第一行（```json 或 ```）和最后一行（```）
        content = "\n".join(lines[1:-1])

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果 JSON 解析失败，尝试提取 JSON 部分
        import re
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            return json.loads(match.group())
        raise RuntimeError(f"AI 返回格式异常，无法解析 JSON:\n{content[:300]}")


def analyze_stocks(config: Dict, stock_list: List[Dict]) -> List[Dict]:
    """逐只分析股票"""
    ai_cfg = config.get("ai", {})
    model = ai_cfg.get("model", "deepseek-chat")
    client = get_client(config)

    results = []
    total = len(stock_list)

    for idx, stock in enumerate(stock_list, 1):
        code = stock["code"]
        name = stock.get("name", code)
        print(f"\n[{idx}/{total}] {name}（{code}）")

        try:
            # 1. 抓数据
            print(f"  抓取行情数据...")
            data = fetch_stock_data(code)

            # 2. AI 分析
            print(f"  AI 分析中...")
            prompt = build_analysis_prompt(data)
            analysis = call_ai(client, model, prompt)

            results.append({
                "code": code,
                "name": data["name"],
                "success": True,
                "price": data["latest_price"],
                "change_pct": data["change_pct"],
                "ma5": data["ma5"],
                "ma10": data["ma10"],
                "ma20": data["ma20"],
                "score": int(analysis.get("score", 50)),
                "trend": analysis.get("trend", "—"),
                "advice": analysis.get("advice", "—"),
                "summary": analysis.get("summary", "—"),
                "detail": analysis.get("detail", "—"),
                "risk": analysis.get("risk", "—"),
            })
            print(f"  ✓ 评分={results[-1]['score']} | {results[-1]['advice']}")

        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results.append({
                "code": code,
                "name": name,
                "success": False,
                "error": str(e),
            })

    return results


# ========================================================
# 4. 报告生成
# ========================================================

def generate_markdown(results: List[Dict], generated_at: str) -> str:
    """生成 Markdown 报告"""
    date_short = generated_at[:10]

    lines = [
        f"# 📊 定投周报 | {date_short}",
        "",
        f"> 生成时间：{generated_at}",
        "> 本报告由 AI 自动生成，仅供参考，不构成投资建议。",
        "",
        "---",
        "",
        "## 📈 评分总览",
        "",
        "| 基金 | 代码 | 评分 | 最新价 | 涨跌 | 建议 |",
        "|------|------|:----:|:------:|:----:|------|",
    ]

    for r in results:
        if r["success"]:
            score = r["score"]
            if score >= 70:
                emoji = "🟢"
            elif score >= 50:
                emoji = "🟡"
            else:
                emoji = "🔴"

            pct = r.get("change_pct", 0)
            pct_str = f"+{pct}%" if pct > 0 else f"{pct}%"
            lines.append(
                f"| {emoji} {r['name']} | {r['code']} | **{score}** | {r['price']} | {pct_str} | {r['advice']} |"
            )
        else:
            lines.append(
                f"| ❌ {r['name']} | {r['code']} | — | — | — | 分析失败 |"
            )

    lines.extend([
        "",
        "---",
        "",
        "## 💡 定投建议汇总",
        "",
    ])

    # 分类
    buy_add = []
    hold_continue = []
    watch = []
    failed = []

    for r in results:
        if not r["success"]:
            failed.append(r)
            continue
        advice = r.get("advice", "")
        if "加仓" in advice:
            buy_add.append(r)
        elif "继续" in advice or "持有" in advice:
            hold_continue.append(r)
        elif "观望" in advice or "减仓" in advice:
            watch.append(r)
        else:
            hold_continue.append(r)

    if buy_add:
        lines.append("### ✅ 建议加仓")
        for r in buy_add:
            lines.append(f"- **{r['name']}**（{r['code']}）— 评分 {r['score']}：{r['summary']}")
        lines.append("")

    if hold_continue:
        lines.append("### 🔄 继续定投")
        for r in hold_continue:
            lines.append(f"- **{r['name']}**（{r['code']}）— 评分 {r['score']}：{r['summary']}")
        lines.append("")

    if watch:
        lines.append("### ⏸️ 建议观望")
        for r in watch:
            lines.append(f"- **{r['name']}**（{r['code']}）— 评分 {r['score']}：{r['summary']}")
        lines.append("")

    if failed:
        lines.append("### ⚠️ 分析失败")
        for r in failed:
            lines.append(f"- **{r['name']}**（{r['code']}）：{r.get('error', '未知')}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 📝 详细分析",
        "",
    ])

    for r in results:
        if not r["success"]:
            lines.append(f"### {r['name']}（{r['code']}）")
            lines.append(f"> ⚠️ 失败：{r.get('error', '未知')}")
            lines.append("")
            continue

        lines.extend([
            f"### {r['name']}（{r['code']}）",
            "",
            f"- **最新价**：{r['price']}（{r.get('change_pct', 0):+.2f}%）",
            f"- **均线**：MA5={r['ma5']}  MA10={r['ma10']}  MA20={r['ma20']}",
            f"- **评分**：{r['score']}/100",
            f"- **趋势**：{r['trend']}",
            f"- **建议**：{r['advice']}",
            "",
            f"> {r['detail']}",
            "",
            f"⚠️ 风险：{r['risk']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        f"*报告由 AI 自动生成于 {generated_at}*",
    ])

    return "\n".join(lines)


def generate_html(results: List[Dict], generated_at: str) -> str:
    """生成简洁 HTML 网页"""
    date_short = generated_at[:10]

    table_rows = []
    for r in results:
        if r["success"]:
            score = r["score"]
            if score >= 70:
                sc = "score-high"
                emoji = "🟢"
            elif score >= 50:
                sc = "score-mid"
                emoji = "🟡"
            else:
                sc = "score-low"
                emoji = "🔴"
            pct = r.get("change_pct", 0)
            pct_str = f"+{pct}%" if pct > 0 else f"{pct}%"
            pct_cls = "up" if pct >= 0 else "down"
            table_rows.append(f"""<tr>
                <td>{emoji} {r['name']}</td>
                <td class="code">{r['code']}</td>
                <td><span class="score-circle {sc}">{score}</span></td>
                <td>{r['price']}</td>
                <td class="{pct_cls}">{pct_str}</td>
                <td class="advice">{r['advice']}</td>
            </tr>""")
        else:
            table_rows.append(f"""<tr class="fail">
                <td>❌ {r['name']}</td>
                <td class="code">{r['code']}</td>
                <td colspan="4">分析失败：{r.get('error', '未知')}</td>
            </tr>""")

    # 详情卡片
    cards = []
    for r in results:
        if not r["success"]:
            continue
        cards.append(f"""<div class="card">
            <h3>{r['name']} <span class="code">{r['code']}</span></h3>
            <div class="meta">
                <span>最新价：<strong>{r['price']}</strong></span>
                <span>评分：<strong>{r['score']}</strong>/100</span>
                <span>趋势：{r['trend']}</span>
                <span>建议：<strong>{r['advice']}</strong></span>
            </div>
            <p>{r['detail']}</p>
            <p class="risk">⚠️ {r['risk']}</p>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>定投周报 | {date_short}</title>
<style>
* {{ box-sizing:border-box;margin:0;padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#333;line-height:1.6;max-width:780px;margin:0 auto;padding:20px; }}
.header {{ text-align:center;padding:28px 20px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:12px;margin-bottom:20px; }}
.header h1 {{ font-size:24px;margin-bottom:6px; }}
.header .date {{ font-size:14px;opacity:.9; }}
.alert {{ background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:13px;color:#856404; }}
.table-wrap {{ background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:22px; }}
table {{ width:100%;border-collapse:collapse;font-size:14px; }}
th {{ background:#fafafa;text-align:left;padding:11px 14px;font-weight:600;color:#666;border-bottom:2px solid #eee; }}
td {{ padding:10px 14px;border-bottom:1px solid #f0f0f0; }}
tr:last-child td {{ border-bottom:none; }}
tr.fail td {{ color:#999;font-style:italic; }}
.code {{ font-family:monospace;font-size:12px;color:#999; }}
.score-circle {{ display:inline-block;width:38px;height:38px;line-height:38px;text-align:center;border-radius:50%;font-weight:700;font-size:15px; }}
.score-high {{ background:#e8f5e9;color:#2e7d32;border:2px solid #4caf50; }}
.score-mid {{ background:#fff8e1;color:#f57f17;border:2px solid #ffc107; }}
.score-low {{ background:#fbe9e7;color:#c62828;border:2px solid #ef5350; }}
.up {{ color:#d0021b;font-weight:500; }}
.down {{ color:#1a7f37;font-weight:500; }}
.advice {{ font-weight:600; }}
.card {{ background:#fff;border-radius:8px;padding:16px 20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06); }}
.card h3 {{ font-size:16px;margin-bottom:8px; }}
.card .code {{ font-size:12px;color:#999;background:#f5f5f5;padding:2px 8px;border-radius:4px;margin-left:6px; }}
.card .meta {{ display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:#666;margin-bottom:10px; }}
.card p {{ font-size:14px;color:#444;line-height:1.75; }}
.card .risk {{ font-size:13px;color:#856404;margin-top:6px; }}
.footer {{ text-align:center;font-size:12px;color:#bbb;padding:20px 0; }}
@media(max-width:600px){{ body {{ padding:10px; }} .header h1 {{ font-size:20px; }} table {{ font-size:12px; }} th,td {{ padding:6px 8px; }} }}
</style>
</head>
<body>
<div class="header"><h1>📊 定投周报</h1><div class="date">{date_short}</div></div>
<div class="alert">⚠️ 本报告由 AI 自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。</div>
<div class="table-wrap">
<table>
<thead><tr><th>基金</th><th>代码</th><th>评分</th><th>最新价</th><th>涨跌</th><th>建议</th></tr></thead>
<tbody>{"".join(table_rows)}</tbody>
</table>
</div>
<h2 style="margin-bottom:12px;">📝 详细分析</h2>
{"".join(cards) if cards else '<p style="color:#999;text-align:center;padding:20px;">暂无分析结果</p>'}
<div class="footer">报告生成时间：{generated_at}<br>Powered by DeepSeek AI · 每周二自动更新</div>
</body>
</html>"""


# ========================================================
# 5. 主流程
# ========================================================

def main():
    parser = argparse.ArgumentParser(description="定投周报生成器（独立版）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不保存文件")
    parser.add_argument("--stocks", help="临时指定股票，逗号分隔（如 510310,588000）")
    args = parser.parse_args()

    print("=" * 50)
    print("📊 定投周报生成器（独立版）")
    print("=" * 50)

    config = load_config()

    # 确定股票列表
    if args.stocks:
        stock_list = [{"code": c.strip(), "name": c.strip()} for c in args.stocks.split(",")]
    else:
        stock_list = config.get("stocks", [])

    if not stock_list:
        print("[错误] 没有配置任何股票")
        sys.exit(1)

    print(f"股票数量：{len(stock_list)} 只")
    for s in stock_list:
        print(f"  {s['code']} — {s['name']}")
    print(f"AI 模型：{config.get('ai', {}).get('provider', 'deepseek')} / {config.get('ai', {}).get('model', 'deepseek-chat')}")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y%m%d")

    # 分析
    print("\n开始分析...")
    results = analyze_stocks(config, stock_list)

    success_count = sum(1 for r in results if r["success"])
    print(f"\n分析完成：成功 {success_count}/{len(results)} 只")

    if args.dry_run:
        print("\n[预览模式] Markdown 报告：\n")
        print(generate_markdown(results, generated_at))
        return

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    md = generate_markdown(results, generated_at)
    md_path = OUTPUT_DIR / f"report_{date_str}.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"\n✓ Markdown: {md_path}")

    html = generate_html(results, generated_at)
    html_path = OUTPUT_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"✓ HTML: {html_path}")

    # 清理旧报告（保留最近 7 份）
    keep = config.get("report", {}).get("keep_history", 7)
    old_reports = sorted(OUTPUT_DIR.glob("report_*.md"), reverse=True)
    for old in old_reports[keep:]:
        old.unlink()
        print(f"  清理旧报告: {old.name}")

    print(f"\n{'=' * 50}")
    print("🎉 报告生成完成！")
    print(f"打开查看: {html_path}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
