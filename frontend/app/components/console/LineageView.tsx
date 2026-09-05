"use client";

import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { RunData } from "@/app/lib/runState";

function AssetNode({ data }: { data: { label: string; status: string; issues: number } }) {
  // Purely check node's own issue count (Phase 2 Fix)
  const isAnomalous = data.issues > 0;
  const isHealthy = data.issues === 0;

  return (
    <div
      className={`min-w-48 rounded-2xl border-2 p-4 shadow-md transition-all ${
        isAnomalous
          ? "border-rose-400 bg-rose-50 text-rose-900"
          : "border-emerald-400 bg-emerald-50 text-emerald-900"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#3E4B8E] !w-3 !h-3" />
      <div className="flex items-center gap-2 text-xs font-extrabold">
        {isAnomalous ? (
          <ShieldAlert size={16} className="text-rose-600 shrink-0" />
        ) : (
          <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
        )}
        <span>{data.label}</span>
      </div>
      <div className="mt-2 text-[11px] font-bold">
        {isAnomalous ? (
          <span className="px-2 py-0.5 rounded-full bg-rose-200 text-rose-800 border border-rose-300">
            {data.issues} issue{data.issues === 1 ? "" : "s"} detected
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-800 border border-emerald-300">
            Healthy (0 issues)
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-[#3E4B8E] !w-3 !h-3" />
    </div>
  );
}

const nodeTypes = { asset: AssetNode };

export function LineageView({ run }: { run: RunData }) {
  if (!run.lineage_graph.nodes.length)
    return (
      <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl p-6 shadow-sm">
        <p className="eyebrow">NO LINEAGE PROVIDED</p>
        <p className="mt-2 text-sm text-[#3D1534]/70 font-medium">
          Upload lineage.json to visualize upstream and downstream topology.
        </p>
      </section>
    );

  const nodes: Node[] = run.lineage_graph.nodes.map((n, i) => ({
    id: n.id,
    type: "asset",
    position: { x: (i % 3) * 260 + 45, y: Math.floor(i / 3) * 190 + 70 },
    data: {
      label: n.label,
      status: n.status,
      issues: n.id === run.root_cause_analysis.failing_table ? run.issues.length : 0,
    },
  }));

  const edges: Edge[] = run.lineage_graph.edges.map((e, i) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    animated:
      e.source === run.root_cause_analysis.failing_table ||
      e.target === run.root_cause_analysis.failing_table,
    style: {
      stroke:
        e.source === run.root_cause_analysis.failing_table ||
        e.target === run.root_cause_analysis.failing_table
          ? "#EF4444"
          : "#3E4B8E",
      strokeWidth: 2.5,
    },
  }));

  return (
    <section className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl overflow-hidden shadow-sm">
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex items-center justify-between">
        <div>
          <p className="eyebrow text-[#A6BCC9]">LINEAGE &amp; IMPACT VECTOR</p>
          <h2 className="text-base font-extrabold text-[#FFF4EB] mt-0.5">Dependency Topology</h2>
        </div>
        <div className="flex gap-2 text-xs font-bold">
          <span className="flex items-center gap-1.5 bg-rose-100 text-rose-800 border border-rose-300 px-2.5 py-1 rounded-full">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" /> Anomalous
          </span>
          <span className="flex items-center gap-1.5 bg-emerald-100 text-emerald-800 border border-emerald-300 px-2.5 py-1 rounded-full">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Healthy
          </span>
        </div>
      </div>

      <div className="h-[400px] bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#A6BCC9" gap={20} size={1} />
          <Controls />
        </ReactFlow>
      </div>

      <div className="border-t border-[#A6BCC9] bg-[#F6E0B6] p-4 text-xs font-bold text-[#3D1534]">
        <span className="font-extrabold text-[#3E4B8E]">Root Cause Origin Candidate: </span>
        {run.root_cause_analysis.root_cause_table}. {run.root_cause_analysis.blast_radius}
      </div>
    </section>
  );
}
