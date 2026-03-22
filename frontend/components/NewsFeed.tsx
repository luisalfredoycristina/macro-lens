"use client";
import { useState } from "react";
import useSWR from "swr";
import { api, CountryNews, NewsArticle } from "../lib/api";

const COUNTRY_LABELS: Record<string, string> = {
  USA: "🇺🇸 US", CHN: "🇨🇳 China", DEU: "🇩🇪 Germany", JPN: "🇯🇵 Japan",
  GBR: "🇬🇧 UK", BRA: "🇧🇷 Brazil", IND: "🇮🇳 India", MEX: "🇲🇽 Mexico",
  KOR: "🇰🇷 Korea", TUR: "🇹🇷 Turkey",
};

const COUNTRIES = Object.keys(COUNTRY_LABELS);

function SentimentBadge({ tone, score }: { tone: string; score: number }) {
  const cfg: Record<string, string> = {
    positive: "bg-emerald-900/50 text-emerald-300 border border-emerald-700",
    negative: "bg-red-900/50 text-red-300 border border-red-700",
    neutral: "bg-gray-700 text-gray-300 border border-gray-600",
  };
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${cfg[tone] ?? cfg.neutral}`}>
      {tone === "positive" ? "↑" : tone === "negative" ? "↓" : "—"} {score}
    </span>
  );
}

function SentimentBar({ score }: { score: number }) {
  // 0=very negative (red), 50=neutral (gray), 100=very positive (green)
  const pct = score;
  let color = "bg-gray-500";
  if (score >= 65) color = "bg-emerald-500";
  else if (score >= 55) color = "bg-emerald-700";
  else if (score <= 35) color = "bg-red-500";
  else if (score <= 45) color = "bg-red-700";

  return (
    <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function ArticleRow({ art }: { art: NewsArticle }) {
  return (
    <a
      href={art.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 py-2.5 border-b border-gray-700/50 last:border-0 group hover:bg-gray-700/30 rounded px-1 -mx-1 transition"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 leading-snug group-hover:text-white line-clamp-2">
          {art.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[11px] text-gray-500">{art.source}</span>
          {art.date && <span className="text-[11px] text-gray-600">{art.date}</span>}
          {art.hawkish && (
            <span className="text-[10px] bg-orange-900/60 text-orange-300 border border-orange-700 px-1.5 rounded-full">HAWK</span>
          )}
          {art.dovish && (
            <span className="text-[10px] bg-blue-900/60 text-blue-300 border border-blue-700 px-1.5 rounded-full">DOVE</span>
          )}
        </div>
      </div>
      <SentimentBadge tone={art.tone} score={art.sentiment_score} />
    </a>
  );
}

function CountryTab({
  code,
  label,
  data,
  active,
  onClick,
}: {
  code: string;
  label: string;
  data: CountryNews | undefined;
  active: boolean;
  onClick: () => void;
}) {
  const tone = data?.dominant_tone ?? "neutral";
  const dot: Record<string, string> = {
    positive: "bg-emerald-400",
    negative: "bg-red-400",
    neutral: "bg-gray-400",
  };
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition ${
        active
          ? "bg-blue-600 text-white"
          : "bg-gray-700/60 text-gray-300 hover:bg-gray-700"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot[tone]}`} />
      {label}
    </button>
  );
}

export default function NewsFeed() {
  const [active, setActive] = useState("USA");
  const { data, error, isLoading } = useSWR("news", () => api.news(COUNTRIES.join(",")), {
    refreshInterval: 300_000,
    revalidateOnFocus: false,
  });

  const newsMap: Record<string, CountryNews> = data?.news ?? {};
  const current = newsMap[active];

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Global News & Sentiment</h2>
        <span className="text-[11px] text-gray-500">via GDELT · 5-day window</span>
      </div>

      {/* Country tabs */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {COUNTRIES.map((cc) => (
          <CountryTab
            key={cc}
            code={cc}
            label={COUNTRY_LABELS[cc]}
            data={newsMap[cc]}
            active={active === cc}
            onClick={() => setActive(cc)}
          />
        ))}
      </div>

      {/* Sentiment overview bar */}
      {current && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-[11px] text-gray-400 whitespace-nowrap">Sentiment</span>
          <SentimentBar score={current.avg_sentiment} />
          <span className="text-[11px] font-mono text-gray-300 whitespace-nowrap">
            {current.avg_sentiment}/100
          </span>
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
              current.dominant_tone === "positive"
                ? "bg-emerald-900/50 text-emerald-300"
                : current.dominant_tone === "negative"
                ? "bg-red-900/50 text-red-300"
                : "bg-gray-700 text-gray-300"
            }`}
          >
            {current.dominant_tone.toUpperCase()}
          </span>
        </div>
      )}

      {/* Articles */}
      <div className="min-h-[160px]">
        {isLoading && (
          <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
            Fetching news…
          </div>
        )}
        {error && (
          <div className="text-sm text-red-400 py-4">
            News unavailable — GDELT may be unreachable.
          </div>
        )}
        {!isLoading && !error && (!current || current.articles.length === 0) && (
          <div className="text-sm text-gray-500 py-4">No recent articles found for this country.</div>
        )}
        {current?.articles.map((art, i) => (
          <ArticleRow key={i} art={art} />
        ))}
      </div>
    </div>
  );
}
