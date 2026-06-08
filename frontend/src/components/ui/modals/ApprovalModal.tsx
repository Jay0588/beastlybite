"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Check, X } from "lucide-react";
import { useStore } from "@/store";
import { toolsAPI } from "@/lib/api";
import { jayWS } from "@/lib/websocket";

export default function ApprovalModal() {
  const { pendingApproval, resolveApproval } = useStore();

  if (!pendingApproval) return null;

  const handleApprove = async () => {
    await toolsAPI.approve(pendingApproval.id);
    jayWS.approveAction(pendingApproval.id);
    resolveApproval(pendingApproval.id);
  };

  const handleDeny = async () => {
    await toolsAPI.deny(pendingApproval.id);
    jayWS.denyAction(pendingApproval.id);
    resolveApproval(pendingApproval.id);
  };

  const levelColor: Record<string, string> = {
    safe: "#22c55e",
    moderate: "#f97316",
    dangerous: "#ef4444",
    critical: "#dc2626",
  };
  const color = levelColor[pendingApproval.level] || "#f97316";

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="w-full max-w-md bg-jay-panel border rounded-2xl shadow-2xl overflow-hidden"
          style={{ borderColor: color + "44" }}
        >
          {/* Header */}
          <div className="px-5 py-4 border-b border-jay-border/40 flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: color + "15" }}>
              <AlertTriangle size={20} style={{ color }} />
            </div>
            <div>
              <div className="text-sm font-semibold text-jay-text">Approval Required</div>
              <div className="text-[10px] font-mono uppercase tracking-widest mt-0.5" style={{ color }}>
                {pendingApproval.level} action
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="px-5 py-4 space-y-3">
            <div>
              <div className="text-[10px] font-mono text-jay-textDim mb-1">TOOL</div>
              <div className="font-mono text-sm text-jay-accent">{pendingApproval.tool}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-jay-textDim mb-1">ACTION</div>
              <div className="text-sm text-jay-text">{pendingApproval.description}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-jay-textDim mb-1">RISK</div>
              <div className="text-sm text-jay-orange/90">{pendingApproval.risk}</div>
            </div>
            {Object.keys(pendingApproval.params || {}).length > 0 && (
              <div>
                <div className="text-[10px] font-mono text-jay-textDim mb-1">PARAMETERS</div>
                <pre className="text-[11px] font-mono text-jay-textDim bg-jay-bg/60 border border-jay-border/30 rounded-lg p-2 overflow-x-auto">
                  {JSON.stringify(pendingApproval.params, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="px-5 py-4 border-t border-jay-border/40 flex gap-3">
            <button
              onClick={handleDeny}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 border border-jay-red/40 text-jay-red hover:bg-jay-red/10 rounded-xl font-mono text-sm transition-colors"
            >
              <X size={16} /> DENY
            </button>
            <button
              onClick={handleApprove}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 border border-jay-green/40 text-jay-green hover:bg-jay-green/10 rounded-xl font-mono text-sm transition-colors"
            >
              <Check size={16} /> APPROVE
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
