import type { EChartsOption } from "echarts";

import { chartPalette } from "@/lib/maps/palette";

/**
 * Shared Apache ECharts base option: recessive grid and axes, portal
 * typography, and a tooltip styled like the site's cards. Series data and
 * colours are supplied by each chart component.
 */
function fontFamily() {
  // ECharts draws on canvas and cannot read CSS variables; use the resolved
  // body font (next/font's hashed Noto Sans family) on the client.
  if (typeof window === "undefined") return "sans-serif";
  return getComputedStyle(document.body).fontFamily || "sans-serif";
}

export function baseChartOption(): EChartsOption {
  const family = fontFamily();
  return {
    animationDuration: 300,
    textStyle: { fontFamily: family, color: chartPalette.text, fontSize: 12 },
    // Right padding leaves room for the last value-axis label.
    grid: { left: 8, right: 32, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      backgroundColor: "#ffffff",
      borderColor: chartPalette.axis,
      borderWidth: 1,
      padding: [6, 10],
      textStyle: { color: chartPalette.text, fontFamily: family, fontSize: 12 },
      extraCssText: "border-radius:3px;box-shadow:0 2px 6px rgba(0,0,0,.08);",
    },
  };
}

export const axisStyle = {
  axisLine: { lineStyle: { color: chartPalette.axis } },
  axisTick: { show: false },
  axisLabel: { color: chartPalette.muted },
  splitLine: { lineStyle: { color: chartPalette.grid } },
} as const;
