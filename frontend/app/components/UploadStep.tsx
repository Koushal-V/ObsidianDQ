"use client";

import React, { useState } from "react";
import { Upload, FileCode, GitBranch, Database, Check, ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

interface UploadStepProps {
  onProceedToTicket: (files: {
    input_file?: string;
    sql_file?: string;
    lineage_file?: string;
    isPreset?: boolean;
  }) => void;
}

export const UploadStep: React.FC<UploadStepProps> = ({ onProceedToTicket }) => {
  const [uploadedFiles, setUploadedFiles] = useState<{
    dataset?: string;
    sql?: string;
    lineage?: string;
  }>({});
  const [usePreset, setUsePreset] = useState(false);
  const [uploadingType, setUploadingType] = useState<string | null>(null);

  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    fileType: "dataset" | "sql" | "lineage"
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingType(fileType);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType);
    try {
      const res = await fetch("http://localhost:8000/api/pipeline/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.status === "success") {
        setUploadedFiles((prev) => ({ ...prev, [fileType]: data.saved_path }));
        setUsePreset(false);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setUploadingType(null);
    }
  };

  const handlePresetSelect = () => {
    setUsePreset(true);
    setUploadedFiles({});
  };

  const canProceed = usePreset || uploadedFiles.dataset || uploadedFiles.sql || uploadedFiles.lineage;

  const uploadCards = [
    {
      key: "dataset" as const,
      icon: <Database className="w-5 h-5 text-[#3E4B8E]" />,
      label: "Dataset File",
      sub: "Raw or staging data source",
      hint: ".csv or .parquet",
      accept: ".csv,.parquet",
      done: !!uploadedFiles.dataset,
      doneLabel: "Dataset Attached",
    },
    {
      key: "sql" as const,
      icon: <FileCode className="w-5 h-5 text-[#3E4B8E]" />,
      label: "Transformation SQL",
      sub: "DuckDB transformation query",
      hint: ".sql file",
      accept: ".sql",
      done: !!uploadedFiles.sql,
      doneLabel: "SQL Attached",
    },
    {
      key: "lineage" as const,
      icon: <GitBranch className="w-5 h-5 text-[#3E4B8E]" />,
      label: "Lineage Topology",
      sub: "Upstream dependency graph",
      hint: ".json topology",
      accept: ".json",
      done: !!uploadedFiles.lineage,
      doneLabel: "Lineage Attached",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="max-w-4xl mx-auto py-6 space-y-8"
    >
      {/* Hero Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#F6E0B6] border border-[#E4CA97] text-[#3D1534] text-xs font-bold shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-[#3E4B8E]" />
          Step 1 of 3 — Data Ingestion Source Configuration
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-[#3D1534]">
          ObsidianDQ Pipeline Ingestion
        </h1>
        <p className="text-sm text-[#3D1534]/70 max-w-lg mx-auto leading-relaxed">
          Upload your dataset, transformation query SQL, and lineage topology — or select our featured demo dataset.
        </p>
      </div>

      {/* Upload Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {uploadCards.map((card, i) => (
          <motion.div
            key={card.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className={`rounded-2xl border-2 p-5 flex flex-col justify-between gap-4 shadow-sm transition-all bg-[#FFF4EB] ${
              card.done
                ? "border-[#3E4B8E] bg-[#3E4B8E]/5 ring-2 ring-[#3E4B8E]/20"
                : "border-[#A6BCC9]/60 hover:border-[#3E4B8E]"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="p-2.5 rounded-xl bg-white border border-[#A6BCC9]/40 shadow-sm">
                {card.icon}
              </div>
              {card.done && (
                <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-300 px-2 py-0.5 rounded-full">
                  <Check className="w-3 h-3 text-emerald-600" /> Attached
                </span>
              )}
            </div>

            <div>
              <h3 className="font-bold text-sm text-[#3D1534]">{card.label}</h3>
              <p className="text-xs text-[#3D1534]/60 mt-0.5">{card.sub}</p>
            </div>

            {/* Input drop area using Powder Blue border & Seashell bg */}
            <label
              className={`flex flex-col items-center justify-center gap-1.5 border-2 border-dashed rounded-xl p-4 cursor-pointer transition-all ${
                uploadingType === card.key
                  ? "border-[#3E4B8E] bg-[#3E4B8E]/10"
                  : card.done
                  ? "border-emerald-400 bg-emerald-50/50"
                  : "border-[#A6BCC9] bg-white hover:border-[#3E4B8E] hover:bg-[#F6E0B6]/30"
              }`}
            >
              <Upload
                className={`w-5 h-5 ${
                  card.done ? "text-emerald-600" : "text-[#3E4B8E]"
                }`}
              />
              <span className="text-xs font-bold text-[#3D1534]">
                {uploadingType === card.key
                  ? "Uploading…"
                  : card.done
                  ? card.doneLabel + " ✓"
                  : "Upload File"}
              </span>
              <span className="text-[10px] font-mono text-[#3D1534]/50">{card.hint}</span>
              <input
                type="file"
                accept={card.accept}
                className="hidden"
                onChange={(e) => handleFileUpload(e, card.key)}
              />
            </label>
          </motion.div>
        ))}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4 my-2">
        <div className="flex-1 h-px bg-[#A6BCC9]/40" />
        <span className="text-xs uppercase font-mono text-[#3D1534]/60 font-bold px-2 py-0.5 bg-[#F6E0B6] rounded-full border border-[#E4CA97]">
          OR SELECT FEATURED DEMO
        </span>
        <div className="flex-1 h-px bg-[#A6BCC9]/40" />
      </div>

      {/* Featured Card (Wheat Background #F6E0B6) */}
      <div
        onClick={handlePresetSelect}
        className={`p-6 rounded-2xl border-2 cursor-pointer transition-all flex items-center justify-between shadow-sm group ${
          usePreset
            ? "border-[#3E4B8E] bg-[#F6E0B6] ring-4 ring-[#3E4B8E]/20"
            : "border-[#E4CA97] bg-[#F6E0B6] hover:border-[#3E4B8E]"
        }`}
      >
        <div className="flex items-center gap-4">
          <div className="p-3 bg-[#3D1534] rounded-xl text-[#FFF4EB] shadow-md">
            <Database className="w-6 h-6 text-[#F6E0B6]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-[#3E4B8E] text-[#FFF4EB]">
                Featured Demo
              </span>
              <h4 className="text-base font-extrabold text-[#3D1534]">
                Synthetic E-Commerce Dataset
              </h4>
            </div>
            <p className="text-xs text-[#3D1534]/80 mt-1 font-medium">
              Includes pre-configured raw_customers.csv · stg_orders.parquet (with nulls &amp; negative prices) · fct_sales.sql
            </p>
          </div>
        </div>

        <div
          className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all ${
            usePreset
              ? "border-[#3E4B8E] bg-[#3E4B8E] text-[#FFF4EB]"
              : "border-[#3D1534]/40 group-hover:border-[#3E4B8E]"
          }`}
        >
          {usePreset && <Check className="w-4 h-4 text-[#FFF4EB]" />}
        </div>
      </div>

      {/* Action Button (French Blue #3E4B8E bg + Seashell #FFF4EB text) */}
      <div className="flex justify-end pt-2">
        <button
          disabled={!canProceed}
          onClick={() =>
            onProceedToTicket({
              input_file: uploadedFiles.dataset,
              sql_file: uploadedFiles.sql,
              lineage_file: uploadedFiles.lineage,
              isPreset: usePreset,
            })
          }
          className="px-7 py-3 text-sm font-extrabold rounded-xl bg-[#3E4B8E] hover:bg-[#2F396E] text-[#FFF4EB] transition-all shadow-md active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
        >
          Proceed to Job Ticket
          <ArrowRight className="w-4 h-4 text-[#F6E0B6]" />
        </button>
      </div>
    </motion.div>
  );
};
