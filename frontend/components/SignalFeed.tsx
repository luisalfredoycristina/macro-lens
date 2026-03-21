import type { MacroSignal } from "../lib/api";
import clsx from "clsx";

interface Props {
  signals: MacroSignal[];
}

const DIRECTION_STYLES = {
  BEARISH: "bg-red-100 text-red-800 border-red-200",
  BULLISH: "bg-teal-100 text-teal-800 border-teal-200",
  NEUTRAL: "bg-gray-100 text-gray-700 border-gray-200",
};

const CONVICTION_DOTS = (c: number) =>
  [1, 2, 3].map((i) => (
    <span key={i} className={clsx("inline-block h-2 w-2 rounded-full", i <= c ? "bg-amber-500" : "bg-gray-200")} />
  ));

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const h = Math.floor(diff / 3_600_000);
  const d = Math.floor(h / 24);
  if (d > 0) return `${d}d ago`;
  if (h > 0) return `${h}h ago`;
  return "just now";
}

export default function SignalFeed({ signals }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm h-full">
      <h2 className="font-semibold text-gray-700 mb-4">Signal Feed</h2>
      {signals.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-gray-400">
          <p className="text-sm">No signals fired yet.</p>
          <p className="text-xs mt-1">Run the fetcher to populate data.</p>
        </div>
      ) : (
        <div className="space-y-3 overflow-y-auto max-h-80">
          {signals.map((signal) => (
            <div key={signal.id} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="font-semibold text-sm text-gray-900">{signal.signal_name}</p>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full border", DIRECTION_STYLES[signal.direction])}>
                    {signal.direction}
                  </span>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{timeAgo(signal.fired_at)}</span>
                </div>
              </div>
              <p className="text-xs text-gray-600 mb-2">{signal.trade_implication}</p>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">Conviction:</span>
                <div className="flex gap-1">{CONVICTION_DOTS(signal.conviction)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
