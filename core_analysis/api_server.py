#!/usr/bin/env python3
# core_analysis/api_server.py
"""
PolyWatch REST API — 供前端（成员 E）调用的 HTTP 接口。

启动方式：
    cd ~/6290
    ./venv/bin/python -m core_analysis.api_server

API 会运行在 http://localhost:5000

所有接口返回 JSON 格式。

Member C — API Layer for Member E (Frontend)
"""
import sys
import os
import json
from datetime import datetime, timezone

# 确保 core_analysis 可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, jsonify, request
from flask_cors import CORS

from core_analysis.db_interface import (
    get_markets_df,
    get_price_series,
    get_active_slugs,
    get_token_id_by_slug,
    query_anomalies,
    get_market_stats,
    get_data_gaps,
)
from core_analysis.zscore_detector import run_zscore_analysis
from core_analysis.benford_detector import (
    run_benford_analysis, prepare_price_changes,
)
from core_analysis.whale_alert import (
    run_whale_analysis, simulate_trades_from_prices,
)

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问


# ── 市场相关 API ────────────────────────────────────────────────

@app.route("/api/markets", methods=["GET"])
def api_markets():
    """
    获取所有市场列表。

    返回:
    [
      {
        "slug": "presidential-election-winner-2024",
        "question": "Will Donald Trump win...",
        "active": true,
        "lastPrice": 0.95,
        "prevPrice": 0.93
      }
    ]
    """
    try:
        df = get_markets_df()
        markets = []
        for _, row in df.iterrows():
            markets.append({
                "slug": row["slug"],
                "question": row["question"],
                "active": bool(row["active"]),
                "lastPrice": float(row["last_price"]),
                "prevPrice": float(row["prev_price"]),
            })
        return jsonify(markets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/markets/<slug>/prices", methods=["GET"])
def api_prices(slug):
    """
    获取某市场的价格历史。

    查询参数:
      since: 可选，ISO 日期字符串（如 "2024-10-01"）
    """
    try:
        since = request.args.get("since")
        df = get_price_series(slug, since=since)
        if df.empty:
            return jsonify([])
        prices = [
            {"time": idx.isoformat(), "price": float(row["price"])}
            for idx, row in df.iterrows()
        ]
        return jsonify(prices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/markets/<slug>/stats", methods=["GET"])
def api_market_stats(slug):
    """
    获取某市场的统计信息。
    """
    try:
        stats = get_market_stats(slug=slug)
        if not stats:
            return jsonify({"error": "market not found"}), 404
        s = stats[0]
        return jsonify({
            "slug": s["slug"],
            "question": s["question"],
            "rowCount": s["row_count"],
            "firstTime": s["first_time"].isoformat() if s["first_time"] else None,
            "lastTime": s["last_time"].isoformat() if s["last_time"] else None,
            "avgPrice": float(s["avg_price"]) if s["avg_price"] else None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/markets/<slug>/gaps", methods=["GET"])
def api_data_gaps(slug):
    """
    获取某市场的数据缺口。
    """
    try:
        gaps = get_data_gaps(slug)
        return jsonify(gaps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 异常事件 API ────────────────────────────────────────────────

@app.route("/api/anomalies", methods=["GET"])
def api_anomalies():
    """
    获取异常事件列表。

    查询参数:
      slug: 可选，按市场筛选
      severity: 可选，按严重程度筛选（low / medium / high）
    """
    try:
        slug = request.args.get("slug")
        severity = request.args.get("severity")
        df = query_anomalies(slug=slug, severity=severity)
        if df.empty:
            return jsonify([])
        events = []
        for _, row in df.iterrows():
            detail = row["detail"]
            if isinstance(detail, str):
                try:
                    detail = json.loads(detail)
                except (json.JSONDecodeError, TypeError):
                    detail = {}
            elif not isinstance(detail, dict):
                detail = {}

            events.append({
                "id": int(row["id"]),
                "marketSlug": row["marketSlug"],
                "detectedAt": row["detectedAt"].isoformat()
                    if hasattr(row["detectedAt"], "isoformat")
                    else str(row["detectedAt"]),
                "eventType": row["eventType"],
                "severity": row["severity"],
                "detail": detail,
            })
        return jsonify(events)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 实时分析 API（按需触发） ────────────────────────────────────

@app.route("/api/analyze/<slug>", methods=["POST"])
def api_analyze(slug):
    """
    对某市场运行实时异常检测（不写入数据库）。

    请求体（可选）:
    {
      "detectors": ["zscore", "benford", "whale"]
    }
    """
    try:
        body = request.get_json(silent=True) or {}
        detectors = body.get("detectors", ["zscore", "benford", "whale"])

        df = get_price_series(slug)
        if df.empty:
            return jsonify({"error": "no data for this market"}), 404

        price_series = df["price"]
        results = {}

        if "zscore" in detectors:
            r = run_zscore_analysis(price_series)
            results["zscore"] = {
                "anomalyCount": r["summary"]["anomaly_points"],
                "anomalyRate": r["summary"]["anomaly_rate"],
                "events": r["events"][:50],  # 最多返回 50 个
            }

        if "benford" in detectors:
            changes = prepare_price_changes(price_series)
            r = run_benford_analysis(changes)
            results["benford"] = {
                "overallConforming": r["analysis"]["overall_conforming"],
                "anomalyWindows": len(r["anomaly_windows"]),
                "summary": r["summary"],
            }

        if "whale" in detectors:
            trades = simulate_trades_from_prices(price_series)
            r = run_whale_analysis(trades, price_series)
            results["whale"] = {
                "whaleTradeCount": r["summary"]["whale_trade_count"],
                "totalTrades": r["summary"]["total_trades"],
                "events": r["events"][:50],
            }

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 健康检查 ────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def api_health():
    """API 健康检查。"""
    return jsonify({"status": "ok", "service": "polywatch-api"})


# ── 服务器启动 ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  PolyWatch API Server")
    print("  http://localhost:5000")
    print("=" * 50)
    print()
    print("可用接口：")
    print("  GET  /api/health                - 健康检查")
    print("  GET  /api/markets               - 市场列表")
    print("  GET  /api/markets/<slug>/prices  - 价格历史")
    print("  GET  /api/markets/<slug>/stats   - 市场统计")
    print("  GET  /api/markets/<slug>/gaps    - 数据缺口")
    print("  GET  /api/anomalies              - 异常事件列表")
    print("  POST /api/analyze/<slug>         - 实时分析")
    print()
    app.run(host="0.0.0.0", port=5000, debug=True)
