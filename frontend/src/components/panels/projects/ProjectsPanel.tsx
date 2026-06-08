"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Plus, FolderOpen, CheckCircle2, Clock, AlertCircle, Scan } from "lucide-react";
import { projectsAPI } from "@/lib/api";
import type { Project, Task } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  todo: "#7ea8cc", in_progress: "#f97316", done: "#22c55e", blocked: "#ef4444"
};
const PRIORITY_COLORS: Record<string, string> = {
  low: "#7ea8cc", medium: "#f97316", high: "#ef4444", critical: "#dc2626"
};

export default function ProjectsPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [view, setView] = useState<"projects" | "tasks">("projects");
  const [newProject, setNewProject] = useState({ name: "", type: "general", path: "" });
  const [newTask, setNewTask] = useState({ title: "", priority: "medium" });
  const [showAdd, setShowAdd] = useState(false);
  const [scanPath, setScanPath] = useState("");
  const [scanResult, setScanResult] = useState<any>(null);

  useEffect(() => {
    projectsAPI.list().then(setProjects).catch(() => {});
    projectsAPI.listTasks().then(setTasks).catch(() => {});
  }, []);

  const createProject = async () => {
    if (!newProject.name) return;
    await projectsAPI.create(newProject);
    const updated = await projectsAPI.list();
    setProjects(updated);
    setNewProject({ name: "", type: "general", path: "" });
    setShowAdd(false);
  };

  const createTask = async () => {
    if (!newTask.title) return;
    await projectsAPI.createTask({
      ...newTask,
      project_id: activeProject?.id,
    });
    const updated = await projectsAPI.listTasks(activeProject?.id);
    setTasks(updated);
    setNewTask({ title: "", priority: "medium" });
  };

  const toggleTask = async (task: Task) => {
    const next = task.status === "done" ? "todo" : "done";
    await projectsAPI.updateTaskStatus(task.id, next);
    setTasks((t) => t.map((x) => x.id === task.id ? { ...x, status: next as any } : x));
  };

  const scanProject = async () => {
    if (!scanPath) return;
    const result = await projectsAPI.scan(scanPath);
    setScanResult(result.output || result);
  };

  const projectTasks = tasks.filter((t) => !activeProject || t.project_id === activeProject.id);

  return (
    <div className="flex h-full gap-4">
      {/* Project list */}
      <div className="w-56 flex-shrink-0 flex flex-col gap-2 border-r border-jay-border/40 pr-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-jay-textDim tracking-widest">PROJECTS</span>
          <button onClick={() => setShowAdd(!showAdd)} className="text-jay-accent hover:text-jay-text">
            <Plus size={14} />
          </button>
        </div>

        {showAdd && (
          <div className="space-y-2 p-2 bg-jay-surface/30 border border-jay-border/30 rounded-lg">
            <input
              value={newProject.name}
              onChange={(e) => setNewProject((p) => ({ ...p, name: e.target.value }))}
              placeholder="Project name"
              className="w-full bg-jay-bg border border-jay-border/50 rounded px-2 py-1 text-xs text-jay-text outline-none"
            />
            <select
              value={newProject.type}
              onChange={(e) => setNewProject((p) => ({ ...p, type: e.target.value }))}
              className="w-full bg-jay-bg border border-jay-border/50 rounded px-2 py-1 text-xs text-jay-text outline-none"
            >
              {["general", "web", "mobile", "api", "trading", "research"].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <input
              value={newProject.path}
              onChange={(e) => setNewProject((p) => ({ ...p, path: e.target.value }))}
              placeholder="Path (optional)"
              className="w-full bg-jay-bg border border-jay-border/50 rounded px-2 py-1 text-xs text-jay-text outline-none"
            />
            <button onClick={createProject} className="w-full py-1 text-xs font-mono bg-jay-accent/10 border border-jay-accent/30 text-jay-accent rounded">
              CREATE
            </button>
          </div>
        )}

        <div className="flex-1 space-y-1 overflow-y-auto">
          <button
            onClick={() => setActiveProject(null)}
            className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
              !activeProject ? "bg-jay-accent/10 text-jay-accent border border-jay-accent/30" : "text-jay-textDim hover:bg-jay-surface/40"
            }`}
          >
            All Projects ({projects.length})
          </button>
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => setActiveProject(p)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                activeProject?.id === p.id ? "bg-jay-accent/10 text-jay-accent border border-jay-accent/30" : "text-jay-textDim hover:bg-jay-surface/40"
              }`}
            >
              <div className="font-semibold truncate">{p.name}</div>
              <div className="text-[10px] text-jay-textMuted capitalize">{p.type}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col gap-3 overflow-hidden">
        {/* Tabs */}
        <div className="flex gap-2 items-center">
          {(["tasks", "scanner"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v as any)}
              className={`px-3 py-1 text-[11px] font-mono rounded transition-all ${
                view === v ? "bg-jay-accent/10 text-jay-accent border border-jay-accent/30" : "text-jay-textDim hover:text-jay-text"
              }`}
            >
              {v.toUpperCase()}
            </button>
          ))}
          {activeProject && (
            <span className="text-xs text-jay-textDim ml-2">— {activeProject.name}</span>
          )}
        </div>

        {view === "tasks" && (
          <div className="flex-1 flex flex-col gap-3 overflow-hidden">
            {/* Add task */}
            <div className="flex gap-2">
              <input
                value={newTask.title}
                onChange={(e) => setNewTask((t) => ({ ...t, title: e.target.value }))}
                onKeyDown={(e) => e.key === "Enter" && createTask()}
                placeholder="Add a task…"
                className="flex-1 bg-jay-surface border border-jay-border/50 rounded-lg px-3 py-1.5 text-sm text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50"
              />
              <select
                value={newTask.priority}
                onChange={(e) => setNewTask((t) => ({ ...t, priority: e.target.value }))}
                className="bg-jay-surface border border-jay-border/50 rounded-lg px-2 text-xs font-mono text-jay-textDim outline-none"
              >
                {["low", "medium", "high", "critical"].map((p) => <option key={p}>{p}</option>)}
              </select>
              <button onClick={createTask} className="px-3 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 rounded-lg text-xs font-mono">
                ADD
              </button>
            </div>

            {/* Task list */}
            <div className="flex-1 overflow-y-auto space-y-2">
              {projectTasks.length === 0 ? (
                <div className="text-center text-jay-textMuted text-sm py-12">No tasks yet</div>
              ) : (
                projectTasks.map((task) => (
                  <motion.div
                    key={task.id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-3 p-3 bg-jay-surface/30 border border-jay-border/30 hover:border-jay-border/50 rounded-xl group"
                  >
                    <button
                      onClick={() => toggleTask(task)}
                      className={`mt-0.5 w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                        task.status === "done"
                          ? "border-jay-green bg-jay-green/20 text-jay-green"
                          : "border-jay-border/60 hover:border-jay-green/50"
                      }`}
                    >
                      {task.status === "done" && <CheckCircle2 size={12} />}
                    </button>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm ${task.status === "done" ? "line-through text-jay-textMuted" : "text-jay-text"}`}>
                        {task.title}
                      </div>
                      {task.description && (
                        <div className="text-xs text-jay-textDim mt-0.5">{task.description}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span
                        className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
                        style={{
                          color: PRIORITY_COLORS[task.priority],
                          borderColor: PRIORITY_COLORS[task.priority] + "44",
                          background: PRIORITY_COLORS[task.priority] + "11",
                        }}
                      >
                        {task.priority}
                      </span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        )}

        {view === "scanner" && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                value={scanPath}
                onChange={(e) => setScanPath(e.target.value)}
                placeholder="/path/to/project"
                className="flex-1 bg-jay-surface border border-jay-border/50 rounded-lg px-3 py-2 text-sm text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50 font-mono"
              />
              <button
                onClick={scanProject}
                className="flex items-center gap-2 px-4 py-2 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 rounded-lg text-sm font-mono"
              >
                <Scan size={14} /> SCAN
              </button>
            </div>
            {scanResult && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-jay-surface/30 border border-jay-border/30 rounded-xl">
                    <div className="text-[10px] font-mono text-jay-textDim mb-2">DETECTED STACK</div>
                    <div className="flex flex-wrap gap-1">
                      {(scanResult.detected_stack || []).map((tech: string) => (
                        <span key={tech} className="text-[11px] font-mono px-1.5 py-0.5 bg-jay-accent/10 border border-jay-accent/20 text-jay-accent rounded">
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 bg-jay-surface/30 border border-jay-border/30 rounded-xl">
                    <div className="text-[10px] font-mono text-jay-textDim mb-2">FILE TYPES</div>
                    <div className="space-y-1">
                      {Object.entries(scanResult.files_by_type || {}).slice(0, 6).map(([ext, count]) => (
                        <div key={ext} className="flex justify-between text-xs font-mono">
                          <span className="text-jay-textDim">{ext || "(no ext)"}</span>
                          <span className="text-jay-text">{count as number}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-jay-surface/30 border border-jay-border/30 rounded-xl">
                  <div className="text-[10px] font-mono text-jay-textDim mb-2">STRUCTURE</div>
                  <div className="flex flex-wrap gap-1">
                    {(scanResult.structure || []).map((item: string) => (
                      <span key={item} className="text-[11px] font-mono text-jay-textDim bg-jay-bg/60 border border-jay-border/30 px-1.5 py-0.5 rounded">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
