"use client";

import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { clsx } from "clsx";
import { RunData } from "@/app/lib/runState";
import { EmptyState, SectionHeader, StatusBadge, toneOf, type Tone } from "@/app/components/obs";

function AssetNode({ data }: { data: { label: string; status: string; issues: number } }) {
  // Base status purely on the node's own issue count (deterministic).
  const tone: Tone = data.issues > 0 ? "critical" : "healthy";
  const t = toneOf(tone);
  return (
    <div className={clsx("min-w-44 rounded-md border-2 px-3 py-2.5 shadow-sm", t.border, t.bg)}>
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-[#3E4B8E]" />
      <div className="flex items-center gap-1.5 text-xs font-bold text-[#3D1534]">
        <span className={clsx("h-2 w-2 rounded-full shrink-0", t.dot)} />
        <span className="min-w-0 truncate">{data.label}</span>
      </div>
      <div className="mt-1 flex items-center gap-1">
        <StatusBadge
          tone={tone}
          dot={false}
          label={data.issues > 0 ? `${data.issues} issue${data.issues === 1 ? "" : "s"}` : "Healthy"}
        />
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-[#3E4B8E]" />
    </div>
  );
}

const nodeTypes = { asset: AssetNode };

export function LineageView({ run }: { run: RunData }) {
  if (!run.lineage_graph.nodes.length) {
    return <EmptyState title="No lineage provided" detail="Upload lineage.json to visualize upstream and downstream topology." />;
  }

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
    <div className="obs-panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <SectionHeader eyebrow="Lineage & impact" title="Dependency topology" />
        <div className="flex items-center gap-2">
          <StatusBadge tone="critical" label="Anomalous" pulse />
          <StatusBadge tone="healthy" label="Healthy" />
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

      <div className="flex items-center gap-2 border-t border-[#A6BCC9]/30 bg-[#F6E0B6]/40 px-3 py-2 text-xs font-medium text-[#3D1534]">
        <span className="font-semibold text-[#5f7180]">Root cause origin candidate:</span>
        <span className="obs-kbd">{run.root_cause_analysis.root_cause_table}</span>
        <span className="text-[#3D1534]/70">{run.root_cause_analysis.blast_radius}</span>
      </div>
    </div>
  );
}