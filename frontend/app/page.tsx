"use client";
import useSWR from "swr";
import { api } from "../lib/api";
import RegimeQuadrant from "../components/RegimeQuadrant";
import IndicatorCard from "../components/IndicatorCard";
import YieldCurveChart from "../components/YieldCurveChart";
import SignalFeed from "../components/SignalFeed";
import CountryTable from "../components/CountryTable";
import CommodityHeatmap from "../components/CommodityHeatmap";

export default function Dashboard() {
  const { data: regime } = useSWR("regime", api.regime, { refreshInterval: 60_000 });
  const { data: indicatorsData } = useSWR("indicators", api.indicators, { refreshInterval: 60_000 });
  const { data: signalsData } = useSWR("signals", () => api.signals(20), { refreshInterval: 30_000 });
  const { data: countriesData } = useSWR("countries", api.countries, { refreshInterval: 300_000 });
  const { data: commoditiesData } = useSWR("commodities", api.commodities, { refreshInterval: 60_000 });

  const indicators = indicatorsData?.indicators ?? [];
  const signals = signalsData?.signals ?? [];
  const countries = countriesData?.countries ?? [];
  const commodities = commoditiesData?.commodities ?? [];

  return (
    <div className="space-y-8">
      {/* Row 1: Regime + Signal Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <RegimeQuadrant regime={regime ?? null} />
        </div>
        <div className="lg:col-span-2">
          <SignalFeed signals={signals} />
        </div>
      </div>

      {/* Row 2: Indicator Cards */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Key Indicators
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {indicators.map((ind) => (
            <IndicatorCard key={ind.series_id} indicator={ind} />
          ))}
        </div>
      </div>

      {/* Row 3: Yield Curve + Commodities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <YieldCurveChart />
        <CommodityHeatmap commodities={commodities} />
      </div>

      {/* Row 4: Country Table */}
      <CountryTable countries={countries} />
    </div>
  );
}
