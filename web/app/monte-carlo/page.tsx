"use client";

import { useState } from "react";

interface PortfolioPosition {
  symbol: string;
  percentage: number;
}

const AVAILABLE_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "META", 
  "NVDA", "TSLA", "BRK.B", "JPM", "V",
  "JNJ", "WMT", "PG", "MA", "UNH"
];

export default function MonteCarloPage() {
  const [positions, setPositions] = useState<PortfolioPosition[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [percentage, setPercentage] = useState<string>("");

  const totalAllocation = positions.reduce((sum, pos) => sum + pos.percentage, 0);
  const remainingAllocation = 100 - totalAllocation;

  const addPosition = () => {
    if (!selectedSymbol || !percentage) return;
    
    const percentValue = parseFloat(percentage);
    if (isNaN(percentValue) || percentValue <= 0) return;
    if (totalAllocation + percentValue > 100) return;

    // Check if symbol already exists
    if (positions.some(p => p.symbol === selectedSymbol)) return;

    setPositions([...positions, { 
      symbol: selectedSymbol, 
      percentage: percentValue 
    }]);
    setSelectedSymbol("");
    setPercentage("");
  };

  const removePosition = (symbol: string) => {
    setPositions(positions.filter(p => p.symbol !== symbol));
  };

  const canRunSimulation = positions.length > 0 && Math.abs(totalAllocation - 100) < 0.01;

  const runSimulation = () => {
    // TODO: Hook up to backend API
    console.log("Running Monte Carlo simulation with positions:", positions);
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
              value={percentage}
              onChange={(e) => setPercentage(e.target.value)}
              placeholder="Allocation %"
              min="0"
              max={remainingAllocation}
              step="0.1"
              className="px-3 py-2 border border-neutral-700 bg-neutral-900 rounded focus:outline-none focus:ring-1 focus:ring-neutral-500 w-32"
            />

            <button
              onClick={addPosition}
              disabled={!selectedSymbol || !percentage || parseFloat(percentage) > remainingAllocation}
              className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed rounded transition-colors"
            >
              Add Position
            </button>
          </div>

          {/* Allocation Status */}
          <div className="mb-4 text-sm">
            <span className={remainingAllocation === 0 ? "text-green-500" : "opacity-60"}>
              Allocated: {totalAllocation.toFixed(1)}% / 100%
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
                    <td className="px-4 py-2 text-right font-mono">{position.percentage.toFixed(1)}%</td>
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

        {/* Simulation Controls */}
        <div className="pt-6 border-t border-neutral-800">
          <button
            onClick={runSimulation}
            disabled={!canRunSimulation}
            className="px-6 py-3 bg-neutral-100 text-neutral-900 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed rounded font-medium transition-colors"
          >
            Run Monte Carlo Simulation
          </button>
          
          {!canRunSimulation && positions.length > 0 && (
            <p className="mt-2 text-sm text-red-400">
              Portfolio must total 100% to run simulation
            </p>
          )}
          
          {positions.length === 0 && (
            <p className="mt-2 text-sm opacity-40">
              Add positions to your portfolio to begin
            </p>
          )}
        </div>
      </div>
    </div>
  );
}