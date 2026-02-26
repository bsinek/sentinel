"use client";

import { useMemo } from "react";

interface PathChartProps {
  projection: {
    confidence_bands: {
      upper_band: number[];
      median_band: number[];
      lower_band: number[];
    };
    sample_paths: number[][];
  };
  nSteps: number;
  alpha: number;
}

const PAD = { top: 20, right: 20, bottom: 32, left: 52 };
const W = 800;
const H = 300;

export default function PathChart({ projection, nSteps, alpha }: PathChartProps) {
  const lowerPercentile = Math.round((1 - alpha) * 100);
  const upperPercentile = Math.round(alpha * 100);
  const { yMin, yMax, yTicks } = useMemo(() => {
    const { sample_paths } = projection;
    
    let lo = Infinity, hi = -Infinity;
    for (const path of sample_paths) {
      for (const v of path) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    
    // Ensure 1.0 is in range
    lo = Math.min(lo, 1.0);
    hi = Math.max(hi, 1.0);
    
    // Calculate distances from 1.0 to data bounds
    const distBelow = 1.0 - lo;
    const distAbove = hi - 1.0;
    const maxDist = Math.max(distBelow, distAbove);
    
    // Create symmetric range around 1.0 with padding
    const padding = maxDist * 0.1;
    const extendedDist = maxDist + padding;
    
    // Calculate uniform tick spacing (5 ticks total, 1.0 in the middle)
    const tickStep = (extendedDist * 2) / 4;
    const yTicks = [
      1.0 - 2 * tickStep,
      1.0 - tickStep,
      1.0,
      1.0 + tickStep,
      1.0 + 2 * tickStep,
    ];
    
    const yMin = yTicks[0];
    const yMax = yTicks[4];

    return { yMin, yMax, yTicks };
  }, [projection]);

  const iW = W - PAD.left - PAD.right;
  const iH = H - PAD.top - PAD.bottom;

  const xScale = (t: number) => (t / (nSteps - 1)) * iW;
  const yScale = (v: number) => iH - ((v - yMin) / (yMax - yMin)) * iH;
  const pts = (path: number[]) => path.map((v, t) => `${xScale(t)},${yScale(v)}`).join(" ");

  const { upper_band, median_band, lower_band } = projection.confidence_bands;

  const bandD = [
    "M",
    upper_band.map((v, t) => `${xScale(t)},${yScale(v)}`).join(" L "),
    "L",
    [...lower_band].reverse().map((v, t) => `${xScale(nSteps - 1 - t)},${yScale(v)}`).join(" L "),
    "Z",
  ].join(" ");

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {/* Y gridlines + labels */}
          {yTicks.map((tick, i) => (
            <g key={i}>
              <line
                x1={0} y1={yScale(tick)} x2={iW} y2={yScale(tick)}
                stroke="currentColor" strokeOpacity={0.08} strokeWidth={1}
              />
              <text
                x={-8} y={yScale(tick)}
                textAnchor="end" dominantBaseline="middle"
                fontSize={10} fill="currentColor" opacity={0.4}
              >
                {tick.toFixed(2)}x
              </text>
            </g>
          ))}

          {/* Simulation paths */}
          {projection.sample_paths.map((path, i) => (
            <polyline
              key={i}
              points={pts(path)}
              fill="none"
              stroke="currentColor"
              strokeOpacity={0.055}
              strokeWidth={0.75}
            />
          ))}

          {/* P10–P90 band */}
          <path d={bandD} fill="currentColor" fillOpacity={0.05} />

          {/* P10 / P90 bounds */}
          <polyline
            points={pts(lower_band)}
            fill="none" stroke="currentColor"
            strokeOpacity={0.3} strokeWidth={1} strokeDasharray="3 3"
          />
          <polyline
            points={pts(upper_band)}
            fill="none" stroke="currentColor"
            strokeOpacity={0.3} strokeWidth={1} strokeDasharray="3 3"
          />

          {/* Median */}
          <polyline
            points={pts(median_band)}
            fill="none" stroke="currentColor"
            strokeOpacity={0.85} strokeWidth={1.5}
          />

          {/* Baseline at 1.0 */}
          {yMin < 1.0 && yMax > 1.0 && (
            <line
              x1={0} y1={yScale(1.0)} x2={iW} y2={yScale(1.0)}
              stroke="currentColor" strokeOpacity={0.18} strokeWidth={1}
              strokeDasharray="4 4"
            />
          )}
        </g>
      </svg>

      <div className="flex gap-6 mt-2 text-xs opacity-40">
        <span>— median</span>
        <span className="opacity-70">--- P{lowerPercentile} / P{upperPercentile}</span>
        <span>{projection.sample_paths.length} paths · {nSteps} steps</span>
      </div>
    </div>
  );
}
