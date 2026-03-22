"use client";
import useSWR from "swr";
import { api } from "../lib/api";
import RegimeQuadrant from "../components/RegimeQuadrant";
import IndicatorCard from "../components/IndicatorCard";
import YieldCurveChart from "../components/YieldCurveChart";
import CountryTable from "../components/CountryTable";
import CommodityHeatmap from "../components/CommodityHeatmap";
import NewsFeed from "../components/NewsFeed";
import InflationNowcast from "../components/InflationNowcast";
import EventsCalendar from "../components/EventsCalendar";
import FOMCAnalysis from "../components/FOMCAnalysis";

export default function Dashboard() {
  const { data: regime } = useSWR("regime", api.regime, { refreshInterval: 60_000 });
  const { data: indicatorsData } = useSWR("indicators", api.indicators, { refreshInterval: 60_000 });
  const { data: countriesData } = useSWR("countries", api.countries, { refreshInterval: 300_000 });
  const { data: commoditiesData } = useSWR("commodities", api.commodities, { refreshInterval: 60_000 });

  const indicators = indicatorsData?.indicators ?? [];
  const countries = countriesData?.countries ?? [];
  const commodities = commoditiesData?.commodities ?? [];

  return (
    <div className="space-y-8">

      {/* ── Row 1: Regime + Events Calendar ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <RegimeQuadrant regime={regime ?? null} />
        </div>
        <div className="lg:col-span-2">
          <EventsCalendar />
        </div>
      </div>

      {/* ── Row 2: Indicator Cards ── */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Key Indicators
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {indicators.map((ind) => (
            <IndicatorCard key={ind.series_id} indicator={ind} />
          ))}
        </div>
      </div>

      {/* ── Row 3: Yield Curve + Commodities ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <YieldCurveChart />
        <CommodityHeatmap commodities={commodities} />
      </div>

      {/* ── Row 4: Inflation Nowcast + FOMC Analysis ── */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Inflation & Fed Policy
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <InflationNowcast />
          <FOMCAnalysis />
        </div>
      </div>

      {/* ── Row 5: News Feed ── */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Global News & Geopolitical Sentiment
        </h2>
        <NewsFeed />
      </div>

      {/* ── Row 6: Country Exposure Table ── */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Country Vulnerability
        </h2>
        <CountryTable countries={countries} />
      </div>

    </div>
  );
}
