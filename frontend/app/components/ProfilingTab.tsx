"use client";

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { BarChart3, CheckCircle2, XCircle, Activity } from "lucide-react";

interface ProfilingMetric {
  column_name: string;
  null_percentage: number;
  distinct_count: number;
  data_type: string;
  status: "PASSED" | "FAILED_EXPECTATION" | string;
}

interface ProfilingTabProps {
  metrics: ProfilingMetric[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#3D1534] border border-[#F6E0B6] rounded-xl px-4 py-3 shadow-lg text-xs text-[#FFF4EB]">
        <div className="font-bold mb-1">{label}</div>
        <div className="text-[#A6BCC9]">
          Null Ratio:{" "}
          <span className="text-[#F6E0B6] font-bold">{payload[0].value}%</span>
        </div>
      </div>
    );
  }
  return null;
};

export const ProfilingTab: React.FC<ProfilingTabProps> = ({ metrics }) => {
  const data = metrics?.length
    ? metrics
    : [
        { column_name: "customer_id", null_percentage: 10.2, distinct_count: 890, data_type: "VARCHAR", status: "FAILED_EXPECTATION" },
        { column_name: "price", null_percentage: 0.0, distinct_count: 4120, data_type: "DOUBLE", status: "FAILED_EXPECTATION" },
        { column_name: "status", null_percentage: 0.0, distinct_count: 5, data_type: "VARCHAR", status: "PASSED" },
        { column_name: "order_date", null_percentage: 0.0, distinct_count: 30, data_type: "DATE", status: "PASSED" },
      ];

  const failedCols = data.filter((d) => d.status === "FAILED_EXPECTATION").length;
  const passedCols = data.length - failedCols;

  return (
    <div className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl shadow-sm overflow-hidden">
      {/* Header Banner (Midnight Violet #3D1534 bg, Seashell #FFF4EB text) */}
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[#3E4B8E] rounded-xl text-[#FFF4EB]">
            <BarChart3 className="w-5 h-5 text-[#F6E0B6]" />
          </div>
          <div>
            <h3 className="font-extrabold text-base text-[#FFF4EB]">Column Distribution &amp; Field Profiling</h3>
            <p className="text-xs text-[#A6BCC9] mt-0.5">
              In-memory field profiling &amp; distinct count expectations computed via DuckDB
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-extrabold bg-rose-500 text-white">
            <XCircle className="w-3 h-3" />
            {failedCols} Failed Expectation
          </span>
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-extrabold bg-emerald-600 text-white">
            <CheckCircle2 className="w-3 h-3" />
            {passedCols} Passed
          </span>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Chart Panel (Wheat Surface #F6E0B6) */}
        <div className="bg-[#F6E0B6] border-2 border-[#E4CA97] rounded-2xl p-5 shadow-sm">
          <div className="text-xs font-extrabold uppercase text-[#3D1534] tracking-wider mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#3E4B8E]" />
            Null Ratio Percentage per Column (%)
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={data}
                margin={{ top: 0, right: 20, left: 20, bottom: 0 }}
              >
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  stroke="#3D1534"
                  tick={{ fontSize: 11, fill: "#3D1534", fontWeight: 700 }}
                  tickFormatter={(v) => `${v}%`}
                />
                <YAxis
                  dataKey="column_name"
                  type="category"
                  stroke="#3D1534"
                  tick={{ fontSize: 11, fill: "#3D1534", fontWeight: 800 }}
                  width={100}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="null_percentage" radius={[0, 6, 6, 0]}>
                  {data.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.status === "FAILED_EXPECTATION" ? "#EF4444" : "#3E4B8E"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-4 mt-3 justify-end text-xs font-bold text-[#3D1534]">
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-2.5 rounded bg-[#EF4444]" />
              Failed Expectation
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-2.5 rounded bg-[#3E4B8E]" />
              Passed (French Blue)
            </div>
          </div>
        </div>

        {/* Data Table Container (Seashell #FFF4EB bg, Powder Blue #A6BCC9 borders) */}
        <div className="bg-[#FFF4EB] border-2 border-[#A6BCC9] rounded-2xl overflow-hidden shadow-sm">
          <div className="px-5 py-3.5 border-b border-[#A6BCC9] bg-[#A6BCC9]/20">
            <h4 className="text-xs font-extrabold uppercase text-[#3D1534] tracking-wider">
              Schema Field Expectation Breakdown
            </h4>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-white border-b border-[#A6BCC9]">
                  {["Column Name", "Data Type", "Null Ratio (%)", "Distinct Count", "Expectation Status"].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-[10px] font-extrabold uppercase tracking-wider text-[#3D1534]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#A6BCC9]/40">
                {data.map((row, idx) => (
                  <tr key={idx} className="hover:bg-white transition-colors">
                    <td className="px-5 py-3.5 font-mono font-extrabold text-[#3D1534] flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          row.status === "FAILED_EXPECTATION"
                            ? "bg-rose-500"
                            : "bg-emerald-500"
                        }`}
                      />
                      {row.column_name}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="px-2.5 py-1 rounded-md bg-[#3E4B8E] text-[#FFF4EB] font-mono text-[10px] font-bold">
                        {row.data_type}
                      </span>
                    </td>
                    <td
                      className={`px-5 py-3.5 font-extrabold ${
                        row.null_percentage > 0 ? "text-rose-600" : "text-emerald-700"
                      }`}
                    >
                      {row.null_percentage.toFixed(1)}%
                    </td>
                    <td className="px-5 py-3.5 font-mono font-bold text-[#3D1534]">
                      {row.distinct_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5">
                      {row.status === "FAILED_EXPECTATION" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-extrabold rounded-full bg-rose-100 text-rose-800 border border-rose-300">
                          <XCircle className="w-3 h-3 text-rose-600" />
                          FAILED EXPECTATION
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-extrabold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          PASSED
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
