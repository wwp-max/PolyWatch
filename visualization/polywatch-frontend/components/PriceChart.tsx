"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { getPriceHistory, getAnomalyEvents } from "@/lib/services";
import { useTheme } from "@/lib/theme";
import type { EChartsOption } from "echarts";

// Dynamic import to avoid SSR issues with echarts
const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface PriceChartProps {
  slug: string;
}

export default function PriceChart({ slug }: PriceChartProps) {
  const prices = getPriceHistory(slug);
  const anomalies = getAnomalyEvents(slug);
  const { theme } = useTheme();

  const isDark = theme === "dark";

  const option: EChartsOption = useMemo(() => {
    const times = prices.map((p) => p.time);
    const values = prices.map((p) => p.price);

    // Build anomaly markPoint data
    const markPointData = anomalies
      .map((a) => {
        // Find the closest price point to the anomaly time
        const anomalyTime = new Date(a.detectedAt).getTime();
        let closestIdx = 0;
        let closestDist = Infinity;
        for (let i = 0; i < prices.length; i++) {
          const dist = Math.abs(
            new Date(prices[i].time).getTime() - anomalyTime,
          );
          if (dist < closestDist) {
            closestDist = dist;
            closestIdx = i;
          }
        }
        const severityColor =
          a.severity === "high"
            ? "#ef4444"
            : a.severity === "medium"
              ? "#eab308"
              : "#3b82f6";

        return {
          coord: [times[closestIdx], values[closestIdx]],
          value: a.severity.toUpperCase(),
          itemStyle: { color: severityColor },
          symbol: "circle",
          symbolSize: a.severity === "high" ? 14 : a.severity === "medium" ? 11 : 8,
          label: { show: false },
          // Store detail for tooltip
          name: `${a.eventType} | ${a.severity}\n${a.detail}`,
        };
      });

    // Theme-aware palette
    const labelColor = isDark ? "#9ca3af" : "#4b5563";
    const axisLineColor = isDark
      ? "rgba(255,255,255,0.15)"
      : "rgba(0,0,0,0.15)";
    const splitLineColor = isDark
      ? "rgba(255,255,255,0.06)"
      : "rgba(0,0,0,0.08)";
    const tooltipBg = isDark ? "rgba(20, 22, 30, 0.95)" : "rgba(255,255,255,0.96)";
    const tooltipBorder = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
    const tooltipTextColor = isDark ? "#e5e7eb" : "#1f2937";
    const tooltipSubColor = isDark ? "#9ca3af" : "#6b7280";
    const accentColor = isDark ? "#38bdf8" : "#2563eb";
    const zoomBorder = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
    const zoomBg = isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)";
    const zoomFill = isDark ? "rgba(56,189,248,0.1)" : "rgba(37,99,235,0.1)";

    return {
      backgroundColor: "transparent",
      grid: {
        top: 40,
        right: 24,
        bottom: 72,
        left: 64,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: tooltipBg,
        borderColor: tooltipBorder,
        textStyle: {
          color: tooltipTextColor,
          fontSize: 14,
          fontFamily: "monospace",
        },
        axisPointer: {
          type: "cross",
          lineStyle: { color: axisLineColor },
          crossStyle: { color: axisLineColor },
        },
        formatter: (params: unknown) => {
          if (Array.isArray(params) && params.length > 0) {
            const p = params[0] as { axisValue: string; value: number };
            const date = new Date(p.axisValue);
            const formatted = date.toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });
            return `<div style="font-family:monospace">
              <div style="color:${tooltipSubColor};margin-bottom:4px;font-size:12px">${formatted}</div>
              <div style="font-size:18px;font-weight:bold;color:${accentColor}">
                ${((p.value as number) * 100).toFixed(2)}%
              </div>
            </div>`;
          }
          return "";
        },
      },
      xAxis: {
        type: "category",
        data: times,
        axisLine: { lineStyle: { color: axisLineColor } },
        axisTick: { show: false },
        axisLabel: {
          color: labelColor,
          fontSize: 12,
          fontFamily: "monospace",
          formatter: (value: string) => {
            const d = new Date(value);
            return `${d.getMonth() + 1}/${d.getDate()}`;
          },
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        min: (value: { min: number }) =>
          Math.max(0, Math.floor(value.min * 20) / 20 - 0.05),
        max: (value: { max: number }) =>
          Math.min(1, Math.ceil(value.max * 20) / 20 + 0.05),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: labelColor,
          fontSize: 12,
          fontFamily: "monospace",
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
        splitLine: {
          lineStyle: { color: splitLineColor, type: "dashed" },
        },
      },
      dataZoom: [
        {
          type: "slider",
          bottom: 8,
          height: 24,
          borderColor: zoomBorder,
          backgroundColor: zoomBg,
          fillerColor: zoomFill,
          dataBackground: {
            lineStyle: { color: isDark ? "rgba(56,189,248,0.3)" : "rgba(37,99,235,0.3)" },
            areaStyle: { color: isDark ? "rgba(56,189,248,0.05)" : "rgba(37,99,235,0.05)" },
          },
          selectedDataBackground: {
            lineStyle: { color: accentColor },
            areaStyle: { color: zoomFill },
          },
          handleStyle: { color: accentColor, borderColor: accentColor },
          textStyle: { color: labelColor, fontSize: 11 },
        },
        {
          type: "inside",
        },
      ],
      series: [
        {
          type: "line",
          data: values,
          smooth: 0.3,
          symbol: "none",
          lineStyle: {
            color: accentColor,
            width: 2,
          },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: isDark ? "rgba(56,189,248,0.15)" : "rgba(37,99,235,0.12)" },
                { offset: 1, color: isDark ? "rgba(56,189,248,0)" : "rgba(37,99,235,0)" },
              ],
            },
          },
          markPoint: {
            data: markPointData,
            tooltip: {
              formatter: ((params: unknown) => {
                const p = params as { name?: string };
                return `<div style="font-family:monospace;max-width:280px;white-space:pre-wrap;font-size:13px;color:${tooltipTextColor}">${p.name ?? ""}</div>`;
              }) as unknown as string,
            },
          },
        },
      ],
    };
  }, [prices, anomalies, isDark]);

  if (prices.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-border bg-card">
        <p className="text-sm text-muted-foreground">
          No price data available for this market.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full rounded-lg border border-border bg-card p-2">
      <ReactECharts
        option={option}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }}
        notMerge={true}
      />
    </div>
  );
}
