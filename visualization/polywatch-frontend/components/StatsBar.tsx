"use client";

import { Card } from "@/components/ui/card";
import { getMarketStats } from "@/lib/services";
import { Activity, AlertTriangle, TrendingUp, DollarSign } from "lucide-react";

interface StatsBarProps {
  slug: string;
}

export default function StatsBar({ slug }: StatsBarProps) {
  const stats = getMarketStats(slug);

  const changePercent = stats.currentPrice
    ? (stats.priceChange / (stats.currentPrice - stats.priceChange)) * 100
    : 0;
  const isUp = stats.priceChange > 0;

  const cards = [
    {
      label: "Current Price",
      value: `${(stats.currentPrice * 100).toFixed(1)}%`,
      sub: `${isUp ? "+" : ""}${changePercent.toFixed(1)}% 24h`,
      subColor: isUp ? "text-positive" : stats.priceChange < 0 ? "text-negative" : "text-muted-foreground",
      icon: DollarSign,
      color: "text-info",
    },
    {
      label: "Data Points",
      value: stats.dataPoints.toLocaleString(),
      icon: Activity,
      color: "text-primary",
    },
    {
      label: "Max Price Swing",
      value: `${(stats.maxSwing * 100).toFixed(1)}%`,
      sub: "single interval",
      icon: TrendingUp,
      color: "text-negative",
    },
    {
      label: "Anomalies Detected",
      value: stats.anomalyCount.toString(),
      sub: stats.active ? "Monitoring active" : "Market ended",
      subColor: stats.active ? "text-positive" : "text-muted-foreground",
      icon: AlertTriangle,
      color: "text-warning",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {cards.map((card) => (
        <Card
          key={card.label}
          className="flex flex-col items-center justify-center border-border bg-card px-3 py-3 text-center"
        >
          <div className={`${card.color} mb-1.5`}>
            <card.icon className="h-5 w-5" />
          </div>
          <p className="text-sm text-muted-foreground">
            {card.label}
          </p>
          <p className="font-mono text-lg font-semibold text-foreground">
            {card.value}
          </p>
          {card.sub && (
            <p className={`text-xs ${card.subColor ?? "text-muted-foreground"}`}>
              {card.sub}
            </p>
          )}
        </Card>
      ))}
    </div>
  );
}
