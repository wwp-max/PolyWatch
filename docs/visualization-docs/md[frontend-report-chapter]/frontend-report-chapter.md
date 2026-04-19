# Frontend-Chapter

## Overview

The PolyWatch frontend is a single-page analytical dashboard that surfaces Polymarket price history together with the anomaly signals produced by the backend detectors. It is designed as a read-only observatory: an analyst selects a market from the sidebar, inspects its price trajectory, and reviews the structured anomaly events that the backend has flagged on that trajectory. The layout prioritises information density over navigation depth, so that the correspondence between a price movement and its explanation is visible on a single screen.

Source Code Location: https://github.com/wwp-max/PolyWatch/tree/main/visualization
Docs Location: https://github.com/wwp-max/PolyWatch/tree/main/docs/visualization-docs

## Technology Stack

The application is built on Next.js 16 with the App Router and React 19, written entirely in TypeScript for end-to-end type safety with the backend contract. Styling uses Tailwind CSS 4 together with shadcn/ui, giving a consistent design system while keeping the component surface minimal. Server communication is handled by TanStack Query, which provides caching, request de-duplication, and a clean loading/error state model for every endpoint. The core time-series visualisation is rendered with Apache ECharts 6, chosen for its mature support of financial-style line charts, interactive tooltips, data-zoom windows, and point-level annotations.

## Architecture

The frontend is organised into three well-separated layers. A thin API layer wraps the four backend endpoints — market listing, per-market price history, per-market statistics, and anomaly events — behind typed fetch functions. On top of that, a hooks layer built with TanStack Query exposes one query hook per endpoint and serves as the single data source for all components; no component fetches data directly. The presentation layer is a flat set of four feature components — the market sidebar, statistics bar, price chart, and anomaly feed — composed by a single root page. A dedicated theme provider persists the user's dark/light preference to local storage and exposes it through React context, which the chart consumes to recompute its colour palette.

![Frontend architecture diagram](./assets/Frontend-architecture-diagram.png)

## Visualization Dashboard

The dashboard uses a two-column layout: a collapsible market sidebar on the left and a vertically scrolling main column on the right containing the header, statistics, price chart, and anomaly feed.

**Market Sidebar.** The left rail lists every tracked market. Each entry shows an active/inactive dot, a truncated market question, the last traded price as a percentage, and the change against the previous price decorated with an up/down/flat trend icon in a semantic colour (green for positive, red for negative, muted for flat). A single click switches the selected market, which drives every other panel on the page. The sidebar can collapse to a narrow rail of status dots to maximise chart real-estate on smaller screens.

**Statistics Bar.** Directly below the market title, four summary cards report the market's average price, total number of recorded data points, first record date, and last record date. Each card carries a distinct icon and accent colour; while data is loading the cards render as animated skeletons so the layout does not reflow when values arrive.

**Price Chart.** The centrepiece of the dashboard is the time-series chart. It draws a smoothed line of the yes-side probability over time with a translucent gradient fill beneath it, and both axes are formatted in domain units — probability as a percentage and time as short month/day labels in a monospace font. A zoom slider along the bottom, together with wheel and drag gestures inside the grid, lets the user inspect any sub-window of the full history without leaving the page. The detected anomalies are overlaid as coloured dot markers whose size and colour encode severity — large red for high, medium yellow, and small blue for low — aligned to the closest price sample by timestamp. The tooltip is custom-rendered: hovering any point shows the formatted timestamp and the exact probability; if that point carries one or more anomaly markers, the tooltip is extended with a coloured section per event containing the event type, severity level, and the underlying detail fields (for example the z-score value, the whale trade size, or the Benford chi-square statistic), so the analyst can read the cause of a price spike without leaving the chart. 

![dashboard-light](./assets/dashboard-light.png)

![chart-anomaly-markers](./assets/chart-anomaly-markers.png)

**Anomaly Feed.** Below the chart, the anomaly feed lists every flagged event for the selected market in reverse chronological order. Each row combines a severity badge colour-coded to match the chart markers, a typed icon for the event category (z-score spike, whale trade, directional bias, or Benford violation), a human-readable label, and the detection timestamp. Beneath the header, each row unfolds the event's structured detail payload as key–value chips. The feed is tightly coupled to the chart: both panels describe the same market and the same set of events, giving the user a two-way reading — visual on top, tabular below.

![anomaly-feed-detail](./assets/anomaly-feed-detail.png)

**Theming.** A toggle in the header switches the whole interface between a dark and a light palette. Both palettes are expressed through CSS variables, and the chart will recompute its axis labels, tooltip background, gradient fill, and zoom-bar colours whenever the context value updates.

![light-dark-theme](./assets/light-dark-theme.png)
