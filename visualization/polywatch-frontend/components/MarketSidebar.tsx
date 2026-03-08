"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { getMarkets } from "@/lib/services";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Circle,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

interface MarketSidebarProps {
  selectedSlug: string;
  onSelectMarket: (slug: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function MarketSidebar({
  selectedSlug,
  onSelectMarket,
  collapsed,
  onToggleCollapse,
}: MarketSidebarProps) {
  const markets = getMarkets();

  return (
    <div className="flex h-full flex-col bg-card">
      {/* Header with collapse toggle */}
      <div className="flex items-center justify-between border-b border-border px-3 py-3">
        {!collapsed && (
          <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Markets
          </h2>
        )}
        <button
          onClick={onToggleCollapse}
          className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Market list */}
      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-1 p-2">
          {markets.map((market) => {
            const isSelected = market.slug === selectedSlug;
            const change = market.lastPrice - market.prevPrice;
            const changePercent = market.prevPrice
              ? (change / market.prevPrice) * 100
              : 0;
            const isUp = change > 0;
            const isFlat = change === 0;

            // Collapsed view: just a colored dot
            if (collapsed) {
              return (
                <button
                  key={market.slug}
                  onClick={() => onSelectMarket(market.slug)}
                  className={`flex items-center justify-center rounded-md p-2 transition-colors ${
                    isSelected
                      ? "bg-accent text-accent-foreground"
                      : "text-foreground hover:bg-accent/50"
                  }`}
                  title={market.question}
                >
                  <Circle
                    className={`h-3 w-3 shrink-0 fill-current ${
                      market.active
                        ? "text-positive"
                        : "text-muted-foreground"
                    }`}
                  />
                </button>
              );
            }

            // Expanded view
            const shortName =
              market.question.length > 40
                ? market.question.slice(0, 37) + "..."
                : market.question;

            return (
              <button
                key={market.slug}
                onClick={() => onSelectMarket(market.slug)}
                className={`group flex w-full flex-col gap-1.5 rounded-md px-3 py-3 text-left transition-colors ${
                  isSelected
                    ? "bg-accent text-accent-foreground"
                    : "text-foreground hover:bg-accent/50"
                }`}
              >
                {/* Market name + active indicator */}
                <div className="flex items-start gap-2">
                  <Circle
                    className={`mt-1.5 h-2.5 w-2.5 shrink-0 fill-current ${
                      market.active
                        ? "text-positive"
                        : "text-muted-foreground"
                    }`}
                  />
                  <span className="text-sm font-medium leading-snug">
                    {shortName}
                  </span>
                </div>

                {/* Price + change */}
                <div className="flex items-center justify-between pl-5">
                  <span className="font-mono text-base font-bold">
                    {(market.lastPrice * 100).toFixed(1)}%
                  </span>
                  <span
                    className={`flex items-center gap-0.5 font-mono text-sm font-medium ${
                      isFlat
                        ? "text-muted-foreground"
                        : isUp
                          ? "text-positive"
                          : "text-negative"
                    }`}
                  >
                    {isFlat ? (
                      <Minus className="h-3.5 w-3.5" />
                    ) : isUp ? (
                      <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    {isFlat ? "0.0" : changePercent > 0 ? "+" : ""}
                    {changePercent.toFixed(1)}%
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
