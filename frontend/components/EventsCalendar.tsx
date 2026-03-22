"use client";
import useSWR from "swr";
import { api, MacroEvent } from "../lib/api";

const CAT_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  central_bank: { label: "Central Bank", color: "text-blue-300",   bg: "bg-blue-900/40 border-blue-700",   icon: "🏦" },
  labor:        { label: "Labor",         color: "text-green-300",  bg: "bg-green-900/40 border-green-700", icon: "👷" },
  inflation:    { label: "Inflation",     color: "text-orange-300", bg: "bg-orange-900/40 border-orange-700", icon: "📈" },
  growth:       { label: "Growth",        color: "text-purple-300", bg: "bg-purple-900/40 border-purple-700", icon: "📊" },
};

const IMP_DOTS: Record<string, string> = {
  high:   "bg-red-400",
  medium: "bg-yellow-400",
  low:    "bg-gray-500",
};

function EventRow({ event }: { event: MacroEvent }) {
  const cfg = CAT_CONFIG[event.category] ?? CAT_CONFIG.growth;
  const isPast = event.days_away < 0;
  const isToday = event.days_away === 0;
  const isSoon = event.days_away >= 0 && event.days_away <= 7;

  return (
    <div
      className={`flex gap-3 py-3 border-b border-gray-700/50 last:border-0 ${isPast ? "opacity-50" : ""}`}
    >
      {/* Date column */}
      <div className="w-14 flex-shrink-0 text-center">
        <div className={`text-xs font-bold ${isToday ? "text-yellow-400" : isSoon ? "text-white" : "text-gray-400"}`}>
          {new Date(event.date + "T12:00:00Z").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
        </div>
        <div className={`text-[10px] mt-0.5 ${isToday ? "text-yellow-500" : "text-gray-600"}`}>
          {isToday ? "TODAY" : isPast ? `${Math.abs(event.days_away)}d ago` : `in ${event.days_away}d`}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.color}`}>
            {cfg.icon} {cfg.label}
          </span>
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${IMP_DOTS[event.importance]}`} />
          {isSoon && !isPast && (
            <span className="text-[10px] bg-yellow-900/50 text-yellow-300 border border-yellow-700 px-2 py-0.5 rounded-full">
              UPCOMING
            </span>
          )}
        </div>
        <p className="text-sm text-gray-200 font-medium mt-1 leading-tight">{event.event}</p>
        <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{event.description}</p>
      </div>
    </div>
  );
}

export default function EventsCalendar() {
  const { data, isLoading } = useSWR("events", api.events, {
    refreshInterval: 3_600_000,
    revalidateOnFocus: false,
  });

  const events = data?.events ?? [];
  const upcoming = events.filter((e) => e.days_away >= 0);
  const past = events.filter((e) => e.days_away < 0).slice(-3);

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Macro Events Calendar</h2>
        <div className="flex items-center gap-3 text-[10px] text-gray-500">
          <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" /> High</span>
          <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-yellow-400 inline-block" /> Med</span>
        </div>
      </div>

      {isLoading && (
        <div className="text-sm text-gray-500 py-6 text-center">Loading calendar…</div>
      )}

      {!isLoading && events.length === 0 && (
        <div className="text-sm text-gray-500 py-4">No events data available.</div>
      )}

      {/* Recent past */}
      {past.length > 0 && (
        <div className="mb-2">
          <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-1">Recent</p>
          {past.map((e, i) => <EventRow key={i} event={e} />)}
        </div>
      )}

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <div>
          {past.length > 0 && <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-3 mb-1">Upcoming</p>}
          {upcoming.map((e, i) => <EventRow key={i} event={e} />)}
        </div>
      )}
    </div>
  );
}
