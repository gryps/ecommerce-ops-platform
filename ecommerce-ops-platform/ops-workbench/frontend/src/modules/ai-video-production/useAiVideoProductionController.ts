import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { ImageProduct, ImageTask } from "../../types";
import type { Asset, GenerationTask, ProductProject, Shot, TaskEvent, WorkbenchStore, WorkflowTemplate } from "./types";

const emptyStore: WorkbenchStore = { projects: [], assets: [], shots: [], tasks: [] };

export function useAiVideoProductionController() {
  const [store, setStore] = useState<WorkbenchStore>(emptyStore);
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [imageProducts, setImageProducts] = useState<ImageProduct[]>([]);
  const [imageTasks, setImageTasks] = useState<ImageTask[]>([]);
  const [taskEvents, setTaskEvents] = useState<Record<string, TaskEvent[]>>({});
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("空闲");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const next = await api<WorkbenchStore>("/ai-video/workbench");
      setStore(next);
      setSelectedProjectId(current => current || next.projects[0]?.id || "");
      setMessage("数据已同步");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadWorkflows = useCallback(async () => {
    try {
      const next = await api<WorkflowTemplate[]>("/ai-video/workflows");
      setWorkflows(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "工作流注册表加载失败");
    }
  }, []);

  const loadImageProductionAssets = useCallback(async () => {
    try {
      const [products, tasks] = await Promise.all([
        api<{ items: ImageProduct[] }>("/images/products"),
        api<{ items: ImageTask[] }>("/images/tasks"),
      ]);
      setImageProducts(products.items);
      setImageTasks(tasks.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "图片生产商品图加载失败");
    }
  }, []);

  useEffect(() => {
    refresh();
    loadWorkflows();
    loadImageProductionAssets();
  }, [refresh, loadWorkflows, loadImageProductionAssets]);

  const selectedProject = useMemo(
    () => store.projects.find(project => project.id === selectedProjectId) || store.projects[0] || null,
    [selectedProjectId, store.projects],
  );
  const selectedAssets = useMemo(
    () => store.assets.filter(asset => asset.project_id === selectedProject?.id),
    [selectedProject?.id, store.assets],
  );
  const selectedProductAssets = useMemo(
    () => selectedAssets.filter(asset => asset.kind === "product"),
    [selectedAssets],
  );
  const selectedShots = useMemo(
    () => store.shots.filter(shot => shot.project_id === selectedProject?.id).sort((a, b) => a.order - b.order),
    [selectedProject?.id, store.shots],
  );
  const selectedTasks = useMemo(
    () => store.tasks.filter(task => task.project_id === selectedProject?.id),
    [selectedProject?.id, store.tasks],
  );

  function actionError(reason: unknown, fallback: string): never {
    const next = reason instanceof Error ? reason.message : fallback;
    setError(next);
    setMessage(next);
    throw reason;
  }

  async function createProject(payload: Pick<ProductProject, "name" | "product_name" | "selling_points" | "audience" | "tone">) {
    setError("");
    setLoading(true);
    try {
      const project = await api<ProductProject>("/ai-video/projects", { method: "POST", body: JSON.stringify(payload) });
      setSelectedProjectId(project.id);
      setMessage("项目已创建");
      await refresh();
      return project;
    } catch (reason) {
      actionError(reason, "项目创建失败");
    } finally {
      setLoading(false);
    }
  }

  async function deleteProject(projectId: string) {
    setError("");
    setLoading(true);
    try {
      await api<void>(`/ai-video/projects/${projectId}`, { method: "DELETE" });
      setSelectedProjectId(current => current === projectId ? "" : current);
      setTaskEvents(current => {
        const taskIds = new Set(store.tasks.filter(task => task.project_id === projectId).map(task => task.id));
        return Object.fromEntries(Object.entries(current).filter(([taskId]) => !taskIds.has(taskId)));
      });
      setMessage("项目已删除");
      await refresh();
    } catch (reason) {
      actionError(reason, "项目删除失败");
    } finally {
      setLoading(false);
    }
  }

  async function draftShots() {
    if (!selectedProject) return;
    setError("");
    setLoading(true);
    try {
      const shots = await api<Shot[]>("/ai-video/director/draft-shots", { method: "POST", body: JSON.stringify({ project_id: selectedProject.id }) });
      setMessage("导演分镜已生成");
      await refresh();
      return shots;
    } catch (reason) {
      actionError(reason, "导演分镜生成失败");
    } finally {
      setLoading(false);
    }
  }

  async function addAsset(kind: string, name: string, notes: string) {
    if (!selectedProject) return;
    setError("");
    setLoading(true);
    try {
      const asset = await api<Asset>("/ai-video/assets", {
        method: "POST",
        body: JSON.stringify({ project_id: selectedProject.id, kind, name, notes }),
      });
      setMessage("商品图已登记");
      await refresh();
      return asset;
    } catch (reason) {
      actionError(reason, "资产登记失败");
    } finally {
      setLoading(false);
    }
  }

  async function uploadAsset(kind: string, name: string, notes: string, file: File) {
    if (!selectedProject) return;
    setError("");
    setLoading(true);
    try {
      const form = new FormData();
      form.set("project_id", selectedProject.id);
      form.set("kind", kind);
      form.set("name", name);
      form.set("notes", notes);
      form.set("file", file);
      const asset = await api<Asset>("/ai-video/assets/upload", { method: "POST", body: form });
      setMessage("商品图已上传");
      await refresh();
      return asset;
    } catch (reason) {
      actionError(reason, "资产文件上传失败");
    } finally {
      setLoading(false);
    }
  }

  async function importImageProductionAsset(payload: { product: ImageProduct; task: ImageTask; outputIndex: number }) {
    if (!selectedProject) return;
    const output = payload.task.output_images[payload.outputIndex];
    if (!output) return;
    setError("");
    setLoading(true);
    try {
      const asset = await api<Asset>("/ai-video/assets/from-image-production", {
        method: "POST",
        body: JSON.stringify({
          project_id: selectedProject.id,
          task_id: payload.task.id,
          output_index: payload.outputIndex,
        }),
      });
      setMessage("已引用图片生产商品图");
      await refresh();
      return asset;
    } catch (reason) {
      actionError(reason, "图片生产商品图引用失败");
    } finally {
      setLoading(false);
    }
  }

  async function createTask(workflowName: string, prompt: string, engine = "comfyui", submitAfterCreate = false) {
    if (!selectedProject) return;
    setError("");
    setLoading(true);
    try {
      const task = await api<GenerationTask>("/ai-video/generation/tasks", {
        method: "POST",
        body: JSON.stringify({
          project_id: selectedProject.id,
          engine,
          workflow_name: workflowName,
          prompt,
          input_asset_ids: selectedProductAssets.map(asset => asset.id),
        }),
      });
      if (submitAfterCreate) {
        const submitted = await api<GenerationTask>(`/ai-video/generation/tasks/${task.id}/submit`, { method: "POST" });
        setMessage(submitted.status === "failed" ? `任务提交失败：${submitted.error}` : "生成任务已提交");
        await refresh();
        return submitted;
      }
      setMessage("生成任务已入队");
      await refresh();
      return task;
    } catch (reason) {
      actionError(reason, "生成任务创建失败");
    } finally {
      setLoading(false);
    }
  }

  async function submitTask(taskId: string) {
    setError("");
    setLoading(true);
    try {
      const submitted = await api<GenerationTask>(`/ai-video/generation/tasks/${taskId}/submit`, { method: "POST" });
      setMessage(submitted.status === "failed" ? `任务提交失败：${submitted.error}` : "生成任务已提交");
      await refresh();
      return submitted;
    } catch (reason) {
      actionError(reason, "生成任务提交失败");
    } finally {
      setLoading(false);
    }
  }

  async function refreshTask(taskId: string, options: { silent?: boolean } = {}) {
    if (!options.silent) {
      setError("");
      setLoading(true);
    }
    try {
      const task = await api<GenerationTask>(`/ai-video/generation/tasks/${taskId}/refresh`, { method: "POST" });
      if (!options.silent) setMessage(task.status === "failed" ? `任务刷新失败：${task.error}` : "任务状态已刷新");
      await refresh();
      return task;
    } catch (reason) {
      if (!options.silent) actionError(reason, "生成任务刷新失败");
    } finally {
      if (!options.silent) setLoading(false);
    }
  }

  async function loadTaskEvents(taskId: string) {
    setError("");
    try {
      const events = await api<TaskEvent[]>(`/ai-video/generation/tasks/${taskId}/events`);
      setTaskEvents(current => ({ ...current, [taskId]: events }));
      return events;
    } catch (reason) {
      actionError(reason, "任务事件加载失败");
    }
  }

  async function checkComfyUI() {
    setError("");
    setLoading(true);
    try {
      const result = await api<{ ok: boolean; base_url: string; error?: string }>("/ai-video/comfyui/health");
      const next = result.ok ? `ComfyUI 已连接：${result.base_url}` : `ComfyUI 未连接：${result.error || result.base_url}`;
      setMessage(next);
      return next;
    } catch (reason) {
      actionError(reason, "ComfyUI 连接检测失败");
    } finally {
      setLoading(false);
    }
  }

  return {
    store,
    workflows,
    imageProducts,
    imageTasks,
    taskEvents,
    selectedProject,
    selectedProjectId,
    selectedAssets,
    selectedProductAssets,
    selectedShots,
    selectedTasks,
    loading,
    message,
    error,
    setSelectedProjectId,
    createProject,
    deleteProject,
    addAsset,
    uploadAsset,
    importImageProductionAsset,
    loadImageProductionAssets,
    draftShots,
    createTask,
    submitTask,
    refreshTask,
    loadTaskEvents,
    checkComfyUI,
    refresh,
  };
}


