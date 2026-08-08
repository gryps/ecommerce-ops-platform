import { api } from "../../api";
import type { ImagePrompt, ImageProduct, ImageTask, ImageTemplate, SourceImage } from "../../types";

type RunImageOperation = (work: () => Promise<unknown>, success: string) => Promise<boolean>;

const splitList = (value: string) => value.split(/[,，、\n]/).map(item => item.trim()).filter(Boolean);

export function useImageTaskActions({
  selected,
  currentTemplate,
  model,
  outputPlan,
  reviewIssues,
  reviewComments,
  outputImageTypes,
  setPrompt,
  run,
}: {
  selected: ImageProduct | null;
  currentTemplate: ImageTemplate | null;
  model: string;
  outputPlan: Record<string, number>;
  reviewIssues: Record<string, string>;
  reviewComments: Record<string, string>;
  outputImageTypes: Record<string, string>;
  setPrompt: (value: ImagePrompt | null) => void;
  run: RunImageOperation;
}) {
  async function generatePrompt() {
    if (!selected || !currentTemplate) return;
    await run(() => api<ImagePrompt>(`/images/products/${selected.id}/prompt`, { method: "POST", body: JSON.stringify({ template_id: currentTemplate.id }) }).then(setPrompt), "提示词已生成");
  }

  async function createTaskFromPrompt() {
    if (!selected || !currentTemplate) return;
    await run(() => api(`/images/products/${selected.id}/tasks`, { method: "POST", body: JSON.stringify({ template_id: currentTemplate.id, model, output_plan: outputPlan }) }), "出图方案和模型任务已保存，等待已配置的图片模型执行并回传结果图。");
  }

  async function reviewTask(task: ImageTask, review_status: string) {
    await run(() => api(`/images/tasks/${task.id}/review`, { method: "PATCH", body: JSON.stringify({ review_status, issues: splitList(reviewIssues[task.id] ?? ""), comment: reviewComments[task.id] ?? "" }) }), "审核状态已更新");
  }

  async function controlTask(task: ImageTask, action: "terminate" | "retry") {
    await run(() => api(`/images/tasks/${task.id}/control`, { method: "POST", body: JSON.stringify({ action }) }), action === "terminate" ? "出图任务已终止，已有结果会保留。" : "出图任务已重新进入队列。");
  }

  async function deleteTask(task: ImageTask) {
    await run(() => api(`/images/tasks/${task.id}`, { method: "DELETE" }), "出图任务及其关联结果已删除。");
  }

  async function attachTaskOutputs(task: ImageTask) {
    const result = await api<{ path: string; cancelled: boolean; images: SourceImage[] }>("/human/image-source-files/select", { method: "POST", body: JSON.stringify({ initial_path: "" }) });
    if (result.cancelled || !result.images.length) return;
    const imageType = outputImageTypes[task.id] ?? "白底图";
    await run(() => api(`/images/tasks/${task.id}/outputs`, { method: "POST", body: JSON.stringify({ image_type: imageType, items: result.images }) }), `已关联 ${result.images.length} 张${imageType}结果图。`);
  }

  return {
    generatePrompt,
    createTaskFromPrompt,
    reviewTask,
    controlTask,
    deleteTask,
    attachTaskOutputs,
  };
}
