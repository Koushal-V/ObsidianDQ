"use client";

import React from "react";
import { Database, AlertCircle, CheckCircle2, AlertTriangle, ArrowRight, GitBranch, Sparkles } from "lucide-react";

interface LineageNode {
  id: string;
  label: string;
  status: "HEALTHY" | "FAILED" | "DEGRADED" | string;
}

interface LineageEdge {
  source: string;
  target: string;
}

interface LineageTabProps {
  lineage: {
    nodes: LineageNode[];
    edges: LineageEdge[];
  };
}

const STATUS_CONFIG = {
  HEALTHY: {
    border: "border-emerald-300",
    bg: "bg-emerald-50",
    icon: <CheckCircle2 className="w-4 h-4 text-emerald-600" />,
    badge: "bg-emerald-100 border-emerald-300 text-emerald-800",
    dot: "bg-emerald-500",
    text: "HEALTHY",
  },
  FAILED: {
    border: "border-rose-400",
    bg: "bg-rose-50",
    icon: <AlertCircle className="w-4 h-4 text-rose-600" />,
    badge: "bg-rose-100 border-rose-300 text-rose-800",
    dot: "bg-rose-600",
    text: "ANOMALOUS",
  },
  DEGRADED: {
    border: "border-amber-300",
    bg: "bg-amber-50",
    icon: <AlertTriangle className="w-4 h-4 text-amber-600" />,
    badge: "bg-amber-100 border-amber-300 text-amber-800",
    dot: "bg-amber-500",
    text: "DEGRADED",
  },
};

export const LineageTab: React.FC<LineageTabProps> = ({ lineage }) => {
  const nodes = lineage.nodes?.length
    ? lineage.nodes
    : [
        { id: "raw_customers", label: "raw_customers (CSV)", status: "HEALTHY" },
        { id: "stg_orders", label: "stg_orders (Parquet)", status: "FAILED" },
        { id: "fct_sales", label: "fct_sales (SQL View)", status: "DEGRADED" },
      ];

  const edges = lineage.edges?.length
    ? lineage.edges
    : [
        { source: "raw_customers", target: "stg_orders" },
        { source: "stg_orders", target: "fct_sales" },
      ];

  const hasEdge = (src: string, tgt: string) =>
    edges.some((e) => e.source === src && e.target === tgt);

  const getStatus = (s: string) =>
    STATUS_CONFIG[s as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.HEALTHY;

  const failedCount = nodes.filter((n) => n.status === "FAILED").length;
  const degradedCount = nodes.filter((n) => n.status === "DEGRADED").length;

  return (
    <div className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl shadow-sm overflow-hidden">
      {/* Header Banner (Midnight Violet #3D1534 bg, Seashell #FFF4EB text) */}
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[#3E4B8E] rounded-xl text-[#FFF4EB]">
            <GitBranch className="w-5 h-5 text-[#F6E0B6]" />
          </div>
          <div>
            <h3 className="font-extrabold text-base text-[#FFF4EB]">Upstream Data Lineage Topology</h3>
            <p className="text-xs text-[#A6BCC9] mt-0.5">
              Dependency graph mapping isolated failure vectors
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-[#F6E0B6] text-[#3D1534]">
            {nodes.length} Lineage Nodes
          </span>
          {failedCount > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-rose-500 text-white shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              {failedCount} ANOMALOUS NODE
            </span>
          )}
          {degradedCount > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-amber-400 text-[#3D1534]">
              {degradedCount} DEGRADED
            </span>
          )}
        </div>
      </div>

      {/* Main Node Diagram Area */}
      <div className="p-8">
        <div className="flex flex-wrap items-center justify-center gap-4">
          {nodes.map((node, idx) => {
            const cfg = getStatus(node.status);
            const prevNode = nodes[idx - 1];
            const showArrow = prevNode && hasEdge(prevNode.id, node.id);

            return (
              <React.Fragment key={node.id}>
                {showArrow && (
                  <div className="flex items-center justify-center">
                    <div className="flex items-center gap-1">
                      <div className="w-8 h-0.5 bg-[#3E4B8E]" />
                      <ArrowRight className="w-5 h-5 text-[#3E4B8E] -ml-1" />
                    </div>
                  </div>
                )}
                {/* Node Card (Powder Blue border #A6BCC9, Wheat surface fallback) */}
                <div
                  className={`relative flex flex-col gap-3 p-5 rounded-2xl border-2 ${cfg.border} ${cfg.bg} min-w-[200px] max-w-[240px] shadow-sm`}
                >
                  <span
                    className={`absolute top-3.5 right-3.5 w-2.5 h-2.5 rounded-full ${cfg.dot} ${
                      node.status === "FAILED" ? "animate-ping" : ""
                    }`}
                  />
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-white rounded-xl border border-[#A6BCC9] shadow-sm">
                      <Database className="w-5 h-5 text-[#3E4B8E]" />
                    </div>
                    <div>
                      <div className="text-[10px] text-[#3D1534]/60 font-bold uppercase tracking-wider">Node {idx + 1}</div>
                      <div className="font-mono text-xs font-bold text-[#3D1534] leading-tight">
                        {node.label}
                      </div>
                    </div>
                  </div>
                  <div
                    className={`inline-flex items-center gap-1.5 self-start px-2.5 py-1 rounded-full border text-[10px] font-bold ${cfg.badge}`}
                  >
                    {cfg.icon}
                    {cfg.text}
                  </div>
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* Additional Edge Legend */}
        {edges.filter((e) => {
          const si = nodes.findIndex((n) => n.id === e.source);
          const ti = nodes.findIndex((n) => n.id === e.target);
          return Math.abs(ti - si) > 1;
        }).length > 0 && (
          <div className="mt-8 pt-5 border-t border-[#A6BCC9]/40 bg-[#F6E0B6]/40 p-4 rounded-xl">
            <div className="text-[10px] uppercase font-extrabold text-[#3D1534] tracking-wider mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#3E4B8E]" />
              Additional Cross-Dependency Vectors
            </div>
            <div className="flex flex-wrap gap-2">
              {edges
                .filter((e) => {
                  const si = nodes.findIndex((n) => n.id === e.source);
                  const ti = nodes.findIndex((n) => n.id === e.target);
                  return Math.abs(ti - si) > 1;
                })
                .map((e, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-mono bg-white border border-[#A6BCC9] rounded-lg text-[#3D1534] font-bold shadow-sm"
                  >
                    <span className="text-[#3E4B8E]">{e.source}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#3D1534]" />
                    <span className="text-[#3E4B8E]">{e.target}</span>
                  </span>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
