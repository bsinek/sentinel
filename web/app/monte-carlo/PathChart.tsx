"use client";

import { useMemo } from "react";

interface PathChartProps {
  paths: number[][];
  maxDisplayPaths?: number;
}

const PAD = { top: 20, right: 20, bottom: 32, left: 52 };
const W = 800;
const H = 300;

function normalizePaths(paths: number[][]): number[][] {
  return paths.map((path) => {
    const s0 = path[0];
    return path.map((v) => v / s0);
  });
}

function subsample(paths: number[][], max: number): number[][] {
  if (paths.length <= max) return paths;
  const step = paths.length / max;
  return Array.from({ length: max }, (_, i) => paths[Math.floor(i * step)]);
}

function percentilePath(paths: number[][], p: number): number[] {
  const nSteps = paths[0].length;
  return Array.from({ length: nSteps }, (_, t) => {
    const vals = paths.map((path) => path[t]).sort((a, b) => a - b);
    const idx = Math.min(Math.floor(p * vals.length), vals.length - 1);
    return vals[idx];
  });
}

export default function PathChart({ paths, maxDisplayPaths = 150 }: PathChartProps) {
  const { displayPaths, medianPath, p10Path, p90Path, yMin, yMax } = useMemo(() => {
    const normed = normalizePaths(paths);
    const display = subsample(normed, maxDisplayPaths);

    const medianPath = percentilePath(normed, 0.5);
    const p10Path = percentilePath(normed, 0.1);
    const p90Path = percentilePath(normed, 0.9);

    let lo = Infinity, hi = -Infinity;
    for (const path of normed) {
      for (const v of path) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    const range = hi - lo || 1;
    const yMin = lo - range * 0.02;
    const yMax = hi + range * 0.02;

    return { displayPaths: display, medianPath, p10Path, p90Path, yMin, yMax };
  }, [paths, maxDisplayPaths]);

  const iW = W - PAD.left - PAD.right;
  const iH = H - PAD.top - PAD.bottom;
  const nSteps = paths[0].length;

  const xScale = (t: number) => (t / (nSteps - 1)) * iW;
  const yScale = (v: number) => iH - ((v - yMin) / (yMax - yMin)) * iH;
  const pts = (path: number[]) => path.map((v, t) => `${xScale(t)},${yScale(v)}`).join(" ");

  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (i / 4) * (yMax - yMin));

  const bandD = [
    "M",
    p90Path.map((v, t) => `${xScale(t)},${yScale(v)}`).join(" L "),
    "L",
    [...p10Path].reverse().map((v, t) => `${xScale(nSteps - 1 - t)},${yScale(v)}`).join(" L "),
    "Z",
  ].join(" ");

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 320 }}>
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

          {/* X axis baseline */}
          <line
            x1={0} y1={iH} x2={iW} y2={iH}
            stroke="currentColor" strokeOpacity={0.15} strokeWidth={1}
          />

          {/* Simulation paths */}
          {displayPaths.map((path, i) => (
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
            points={pts(p10Path)}
            fill="none" stroke="currentColor"
            strokeOpacity={0.3} strokeWidth={1} strokeDasharray="3 3"
          />
          <polyline
            points={pts(p90Path)}
            fill="none" stroke="currentColor"
            strokeOpacity={0.3} strokeWidth={1} strokeDasharray="3 3"
          />

          {/* Median */}
          <polyline
            points={pts(medianPath)}
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
        <span className="opacity-70">--- P10 / P90</span>
        <span>{paths.length.toLocaleString()} paths · {nSteps - 1} steps</span>
      </div>
    </div>
  );
}
