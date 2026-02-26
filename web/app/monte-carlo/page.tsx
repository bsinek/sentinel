"use client";

import { useState } from "react";
import PathChart from "./PathChart";

interface Position {
  symbol: string;
  allocation: number;
}

interface MetricsResult {
  mean_return: number;
  median_return: number;
  median_cagr: number;
  volatility: number;
  sharpe: number;
  var: number;
  cvar: number;
  mean_mdd: number;
  worst_mdd: number;
  prob_loss: number;
}

interface ProjectionResult {
  confidence_bands: {
    upper_band: number[];
    median_band: number[];
    lower_band: number[];
  };
  sample_paths: number[][];
}

interface SimulationParams {
  start: string;
  end: string;
  interval: "1d" | "1wk" | "1mo";
  nSteps: string;
  nSims: string;
  alpha: string;
  riskFreeRate: string;
  nSamples: string;
}

const AVAILABLE_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "META", 
  "NVDA", "TSLA", "BRK.B", "JPM", "V",
  "JNJ", "WMT", "PG", "MA", "UNH", "SPY"
];

export default function MonteCarloPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [allocation, setAllocation] = useState<string>("");
  const [metrics, setMetrics] = useState<MetricsResult | null>(null);
  const [projection, setProjection] = useState<ProjectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [params, setParams] = useState<SimulationParams>({
    start: "2022-01-01",
    end: "2026-01-01",
    interval: "1d",
    nSteps: "252",
    nSims: "1000",
    alpha: "0.95",
    riskFreeRate: "0.0",
    nSamples: "50",
  });

  const totalAllocation = positions.reduce((sum, pos) => sum + pos.allocation, 0);
  const remainingAllocation = 100 - totalAllocation;

  const addPosition = () => {
    if (!selectedSymbol || !allocation) return;
    
    const allocationValue = parseFloat(allocation);
    if (isNaN(allocationValue) || allocationValue <= 0) return;
    if (totalAllocation + allocationValue > 100) return;

    // Check if symbol already exists
    if (positions.some(p => p.symbol === selectedSymbol)) return;

    setPositions([...positions, { 
      symbol: selectedSymbol, 
      allocation: Math.round(allocationValue * 10) / 10
    }]);
    setSelectedSymbol("");
    setAllocation("");
  };

  const removePosition = (symbol: string) => {
    setPositions(positions.filter(p => p.symbol !== symbol));
  };

  const fmtPct = (v: number | null, d = 2) =>
    v == null || !isFinite(v) ? "—" : `${(v * 100).toFixed(d)}%`;
  const fmtPctSigned = (v: number | null, d = 2) =>
    v == null || !isFinite(v) ? "—" : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(d)}%`;
  const fmtNum = (v: number | null, d = 3) =>
    v == null || !isFinite(v) ? "—" : v.toFixed(d);

  const canRunSimulation =
    positions.length > 0 &&
    totalAllocation === 100 &&
    !!params.start &&
    !!params.end &&
    parseInt(params.nSteps) > 0 &&
    parseInt(params.nSims) > 0;

  const runSimulation = async () => {
    setLoading(true);
    setMetrics(null);
    setProjection(null);
    const tickers = positions.map(p => p.symbol)
    const weights = positions.map(p => p.allocation / 100)

    try {
      const res = await fetch("http://localhost:8000/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tickers,
          weights,
          start: params.start,
          end: params.end,
          interval: params.interval,
          n_steps: parseInt(params.nSteps),
          n_sims: parseInt(params.nSims),
          alpha: parseFloat(params.alpha),
          risk_free_rate: parseFloat(params.riskFreeRate),
          n_samples: parseInt(params.nSamples),
          include: ["metrics", "projection"],
        }),
      })
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Simulation failed");
      setMetrics(data.metrics);
      if (data.projection) setProjection(data.projection);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-2xl font-semibold mb-2">Monte Carlo Simulation</h1>
          <p className="text-sm opacity-60">
            Construct a portfolio and run Monte Carlo simulation
          </p>
        </header>

        {/* Portfolio Construction */}
        <div className="mb-8">
          <h2 className="text-lg font-medium mb-4">Portfolio Construction</h2>
          
          <div className="flex gap-3 mb-6">
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500"
            >
              <option value="">Select symbol</option>
              {AVAILABLE_SYMBOLS.map(symbol => (
                <option 
                  key={symbol} 
                  value={symbol}
                  disabled={positions.some(p => p.symbol === symbol)}
                >
                  {symbol}
                </option>
              ))}
            </select>

            <input
              type="number"
              value={allocation}
              onChange={(e) => setAllocation(e.target.value)}
              placeholder="Allocation %"
              min="0"
              max={remainingAllocation}
              step="0.1"
              className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 w-32"
            />

            <button
              onClick={addPosition}
              disabled={!selectedSymbol || !allocation || parseFloat(allocation) > remainingAllocation}
              className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed rounded transition-colors cursor-pointer"
            >
              Add Position
            </button>
          </div>

          {/* Allocation Status */}
          <div className="mb-4 text-sm">
            <span className={remainingAllocation === 0 ? "text-green-500" : "opacity-60"}>
              Allocated: {totalAllocation.toFixed(1)}% / 100.0%
            </span>
            {remainingAllocation > 0 && (
              <span className="ml-4 opacity-40">
                Remaining: {remainingAllocation.toFixed(1)}%
              </span>
            )}
          </div>

          {/* Positions Table */}
          <div className="border border-neutral-800 rounded overflow-hidden">
            <table className="w-full table-fixed">
              <thead>
                <tr className="h-8 border-b border-neutral-800 bg-neutral-900/50">
                  <th className="text-left px-4 py-2 font-medium">Symbol</th>
                  <th className="text-right px-4 py-2 font-medium">Allocation</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="h-10 px-4 py-2 text-sm opacity-30 text-center">
                      No positions added
                    </td>
                  </tr>
                ) : positions.map((position) => (
                  <tr key={position.symbol} className="h-10 border-b border-neutral-800 last:border-b-0">
                    <td className="px-4 py-2 font-mono">{position.symbol}</td>
                    <td className="px-4 py-2 text-right font-mono">{position.allocation.toFixed(1)}%</td>
                    <td className="w-20 px-4 py-2 text-right">
                      <button
                        onClick={() => removePosition(position.symbol)}
                        className="text-neutral-500 hover:text-red-400 text-sm transition-colors hover:cursor-pointer"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Simulation Parameters */}
        <div className="mb-8">
          <h2 className="text-lg font-medium mb-4">Simulation Parameters</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4 max-w-lg">
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Start Date</label>
              <input
                type="date"
                value={params.start}
                onChange={(e) => setParams({ ...params, start: e.target.value })}
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">End Date</label>
              <input
                type="date"
                value={params.end}
                onChange={(e) => setParams({ ...params, end: e.target.value })}
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Interval</label>
              <select
                value={params.interval}
                onChange={(e) => setParams({ ...params, interval: e.target.value as SimulationParams["interval"] })}
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              >
                <option value="1d">Daily</option>
                <option value="1wk">Weekly</option>
                <option value="1mo">Monthly</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Simulation Steps</label>
              <input
                type="number"
                value={params.nSteps}
                onChange={(e) => setParams({ ...params, nSteps: e.target.value })}
                min="1"
                step="1"
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Simulations</label>
              <input
                type="number"
                value={params.nSims}
                onChange={(e) => setParams({ ...params, nSims: e.target.value })}
                min="1"
                step="100"
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Alpha (VaR/CVaR)</label>
              <input
                type="number"
                value={params.alpha}
                onChange={(e) => setParams({ ...params, alpha: e.target.value })}
                min="0.01"
                max="0.99"
                step="0.01"
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Risk-Free Rate</label>
              <input
                type="number"
                value={params.riskFreeRate}
                onChange={(e) => setParams({ ...params, riskFreeRate: e.target.value })}
                min="0"
                step="0.001"
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs opacity-50 uppercase tracking-wide">Paths to Display</label>
              <select
                value={params.nSamples}
                onChange={(e) => setParams({ ...params, nSamples: e.target.value })}
                className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 text-sm"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="150">150</option>
                <option value="200">200</option>
                <option value="500">500</option>
              </select>
            </div>
          </div>
        </div>

        {/* Simulation Controls */}
        <div className="pt-6 border-t border-neutral-800">
          <button
            onClick={runSimulation}
            disabled={!canRunSimulation || loading}
            className="px-6 py-3 bg-neutral-100 text-neutral-900 transition-all hover:scale-101 hover:bg-green-100 disabled:opacity-30 disabled:cursor-not-allowed rounded font-medium cursor-pointer active:scale-99"
          >
            {loading ? "Running..." : "Run Monte Carlo Simulation"}
          </button>
          
          {!canRunSimulation && positions.length > 0 && (
            <p className="mt-2 text-sm text-red-400">
              {totalAllocation !== 100
                ? "Portfolio must total 100% to run simulation"
                : !params.start || !params.end
                ? "Start and end dates are required"
                : parseInt(params.nSteps) <= 0
                ? "Step count must be greater than 0"
                : parseInt(params.nSims) <= 0
                ? "Simulation count must be greater than 0"
                : null}
            </p>
          )}
          
          {positions.length === 0 && (
            <p className="mt-2 text-sm opacity-40">
              Add positions to your portfolio to begin
            </p>
          )}
        </div>

        {/* Results */}
        {(metrics || projection) && (
          <div className="mt-8 pt-8 border-t border-neutral-800">
            <h2 className="text-lg font-medium mb-6">Results</h2>

            {/* Portfolio Paths Chart */}
            {projection && (
              <div className="mb-8">
                <p className="text-xs opacity-40 uppercase tracking-wide mb-3">Portfolio Value Paths</p>
                <PathChart projection={projection} nSteps={parseInt(params.nSteps)} alpha={parseFloat(params.alpha)} />
              </div>
            )}

            {metrics && (
            <div className="grid grid-cols-2 gap-x-12 gap-y-3 max-w-lg text-sm">
              <div className="flex justify-between">
                <span className="opacity-50">Mean Return</span>
                <span className="font-mono">{fmtPctSigned(metrics.mean_return)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Median Return</span>
                <span className="font-mono">{fmtPctSigned(metrics.median_return)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Median CAGR</span>
                <span className="font-mono">{fmtPctSigned(metrics.median_cagr)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Volatility</span>
                <span className="font-mono">{fmtPct(metrics.volatility)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Sharpe Ratio</span>
                <span className="font-mono">{fmtNum(metrics.sharpe)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Prob. of Loss</span>
                <span className="font-mono">{fmtPct(metrics.prob_loss, 1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">VaR ({params.alpha})</span>
                <span className="font-mono">{fmtPct(metrics.var)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">CVaR ({params.alpha})</span>
                <span className="font-mono">{fmtPct(metrics.cvar)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Mean Max Drawdown</span>
                <span className="font-mono">{fmtPct(metrics.mean_mdd)}</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-50">Worst Max Drawdown</span>
                <span className="font-mono">{fmtPct(metrics.worst_mdd)}</span>
              </div>
            </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}