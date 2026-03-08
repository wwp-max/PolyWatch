"use client";

import { useState } from "react";
import { Separator } from "@/components/ui/separator";
import StatsBar from "@/components/StatsBar";
import MarketSidebar from "@/components/MarketSidebar";
import PriceChart from "@/components/PriceChart";
import AnomalyFeed from "@/components/AnomalyFeed";
import ThemeToggle from "@/components/ThemeToggle";
import { getMarkets } from "@/lib/services";

export default function Home() {
  const markets = getMarkets();
  const [selectedSlug, setSelectedSlug] = useState(markets[0]?.slug ?? "");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const selectedMarket = markets.find((m) => m.slug === selectedSlug);

  return (
    <div className="flex h-screen bg-background">
      {/* ===== Left sidebar — full height ===== */}
      <aside
        className={`shrink-0 border-r border-border transition-[width] duration-200 ${
          sidebarCollapsed ? "w-14" : "w-56"
        }`}
      >
        <MarketSidebar
          selectedSlug={selectedSlug}
          onSelectMarket={setSelectedSlug}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((p) => !p)}
        />
      </aside>

      {/* ===== Right: header + statsbar + content + footer ===== */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between px-5 py-2.5">
          <div className="flex items-baseline gap-3">
            <h1 className="font-mono text-xl font-bold tracking-tight text-foreground">
              PolyWatch
            </h1>
            <span className="text-sm text-muted-foreground">
              Polymarket Signal Analysis
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="font-mono text-xs text-muted-foreground">
              CS6290 Project
            </span>
            <ThemeToggle />
          </div>
        </header>

        <Separator />

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          {/* Market title */}
          {selectedMarket && (
            <div className="flex flex-wrap items-center gap-2 px-5 pt-4 pb-2">
              <h2 className="text-base font-semibold text-foreground">
                {selectedMarket.question}
              </h2>
              <span className="font-mono text-sm text-muted-foreground">
                {selectedMarket.slug}
              </span>
              {!selectedMarket.active && (
                <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  ENDED
                </span>
              )}
            </div>
          )}

          {/* Per-market StatsBar */}
          <div className="px-5 py-3">
            <StatsBar slug={selectedSlug} />
          </div>

          <Separator />

          {/* Price chart */}
          <div className="h-[420px] shrink-0 px-5 pt-4">
            <PriceChart slug={selectedSlug} />
          </div>

          <Separator className="mx-5 my-3" />

          {/* Anomaly feed */}
          <div className="h-[280px] shrink-0 px-5 pb-4">
            <AnomalyFeed slug={selectedSlug} />
          </div>
        </div>

        {/* Footer */}
        <Separator />
        <footer className="flex items-center justify-center px-5 py-2">
          <p className="font-mono text-xs text-muted-foreground">
            PolyWatch &mdash; Polymarket Signal Analysis &nbsp;|&nbsp; CS6290
            Project &nbsp;|&nbsp; CityU Hong Kong
          </p>
        </footer>
      </div>
    </div>
  );
}
