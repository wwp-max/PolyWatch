"use client";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getAnomalyEvents } from "@/lib/services";
import { AlertTriangle, Waves, Wallet } from "lucide-react";

interface AnomalyFeedProps {
  slug: string;
}

const eventTypeConfig = {
  zscore_spike: {
    label: "Z-Score Spike",
    icon: AlertTriangle,
  },
  whale_alert: {
    label: "Whale Alert",
    icon: Wallet,
  },
  volume_surge: {
    label: "Volume Surge",
    icon: Waves,
  },
} as const;

const severityConfig = {
  high: {
    variant: "destructive" as const,
    className: "bg-red-500/20 text-red-400 border-red-500/30 hover:bg-red-500/20",
  },
  medium: {
    variant: "secondary" as const,
    className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30 hover:bg-yellow-500/20",
  },
  low: {
    variant: "secondary" as const,
    className: "bg-blue-500/20 text-blue-400 border-blue-500/30 hover:bg-blue-500/20",
  },
};

export default function AnomalyFeed({ slug }: AnomalyFeedProps) {
  const anomalies = getAnomalyEvents(slug);

  if (anomalies.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-border bg-card">
        <p className="text-sm text-muted-foreground">
          No anomalies detected for this market.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Anomaly Events
        </h2>
        <span className="font-mono text-xs text-muted-foreground">
          {anomalies.length} detected
        </span>
      </div>
      <ScrollArea className="flex-1">
        <div className="flex flex-col divide-y divide-border">
          {anomalies.map((anomaly) => {
            const typeConf = eventTypeConfig[anomaly.eventType];
            const sevConf = severityConfig[anomaly.severity];
            const Icon = typeConf.icon;
            const date = new Date(anomaly.detectedAt);
            const timeStr = date.toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });

            return (
              <div key={anomaly.id} className="px-4 py-3">
                {/* Top row: severity badge + event type + time */}
                <div className="flex items-center gap-2">
                  <Badge variant={sevConf.variant} className={sevConf.className}>
                    {anomaly.severity.toUpperCase()}
                  </Badge>
                  <div className="flex items-center gap-1 text-sm text-foreground">
                    <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium">{typeConf.label}</span>
                  </div>
                  <span className="ml-auto font-mono text-xs text-muted-foreground">
                    {timeStr}
                  </span>
                </div>

                {/* Detail text */}
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                  {anomaly.detail}
                </p>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
