"use client";

import { Card } from "@/components/ui/card";
import { useMarketStats } from "@/lib/hooks";
import { Activity, BarChart3, Clock, CalendarDays } from "lucide-react";

interface StatsBarProps {
  slug: string;
}

export default function StatsBar({ slug }: StatsBarProps) {
  const { data: stats, isLoading } = useMarketStats(slug);

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card
            key={i}
            className="flex flex-col items-center justify-center border-border bg-card px-3 py-3 text-center"
          >
            <div className="mb-1.5 h-5 w-5 animate-pulse rounded bg-muted" />
            <div className="mb-1 h-4 w-20 animate-pulse rounded bg-muted" />
            <div className="h-6 w-16 animate-pulse rounded bg-muted" />
          </Card>
        ))}
      </div>
    );
  }

  const formatDate = (iso: string | null) => {
    if (!iso) return "N/A";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const cards = [
    {
      label: "Average Price",
      value: stats.avgPrice != null ? `${(stats.avgPrice * 100).toFixed(1)}%` : "N/A",
      icon: BarChart3,
      color: "text-info",
    },
    {
      label: "Data Points",
      value: stats.rowCount.toLocaleString(),
      icon: Activity,
      color: "text-primary",
    },
    {
      label: "First Record",
      value: formatDate(stats.firstTime),
      icon: CalendarDays,
      color: "text-positive",
    },
    {
      label: "Last Record",
      value: formatDate(stats.lastTime),
      icon: Clock,
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
        </Card>
      ))}
    </div>
  );
}
