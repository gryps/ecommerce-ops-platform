import type { Dispatch, SetStateAction } from "react";
import { FolderOpen } from "lucide-react";
import { Pill } from "../../components/Pill";
import type { DeleteConfirmation, ImageProduct, ImageTask } from "../../types";

export function ImageTaskList({
  tasks,
  products,
  busy,
  outputImageTypes,
  reviewIssues,
  reviewComments,
  setOutputImageTypes,
  setReviewIssues,
  setReviewComments,
  attachTaskOutputs,
  reviewTask,
  controlTask,
  deleteTask,
  setConfirmation,
}: {
  tasks: ImageTask[];
  products: ImageProduct[];
  busy: boolean;
  outputImageTypes: Record<string, string>;
  reviewIssues: Record<string, string>;
  reviewComments: Record<string, string>;
  setOutputImageTypes: Dispatch<SetStateAction<Record<string, string>>>;
  setReviewIssues: Dispatch<SetStateAction<Record<string, string>>>;
  setReviewComments: Dispatch<SetStateAction<Record<string, string>>>;
  attachTaskOutputs: (task: ImageTask) => Promise<void>;
  reviewTask: (task: ImageTask, reviewStatus: string) => Promise<void>;
  controlTask: (task: ImageTask, action: "terminate" | "retry") => Promise<void>;
  deleteTask: (task: ImageTask) => Promise<void>;
  setConfirmation: Dispatch<SetStateAction<DeleteConfirmation | null>>;
}) {
  return <div className="image-task-list">
    {tasks.map(task => <article key={task.id}>
      <div><b>{task.template_name}</b><span>{products.find(item => item.id === task.product_id)?.name ?? "未命名产品"} · {task.model || "未记录模型"} · {Object.entries(task.output_plan ?? {}).map(([name, count]) => `${name} ${count} 张`).join(" / ")} · <Pill value={task.status} /> · <Pill value={task.review_status} /></span></div>
      <div className="image-task-progress"><span style={{ width: `${task.status === "completed" || task.status === "archived" ? 100 : 0}%` }} /></div>
      <p>{task.output_images.length ? `已关联 ${task.output_images.length} 张结果图。按图片类型核对主体、结构和平台要求，填写问题后可要求重做。` : "尚未关联结果图。可从本地结果目录选择图片，关联到当前生成任务。"}</p>
      <div className="image-task-output-actions"><select value={outputImageTypes[task.id] ?? "白底图"} onChange={event => setOutputImageTypes(types => ({ ...types, [task.id]: event.target.value }))}>{["白底图", "环境搭配图", "佩戴图", "商详图"].map(type => <option key={type}>{type}</option>)}</select><button type="button" className="human-secondary" disabled={busy} onClick={() => attachTaskOutputs(task)}><FolderOpen />关联本地结果图</button></div>
      {task.output_images.length > 0 && <div className="image-task-result-grid">{task.output_images.map((image, index) => <figure key={`${image.path}-${index}`}><img src={image.url} alt={image.name} /><figcaption>{image.image_type} · {image.name}</figcaption></figure>)}</div>}
      <div className="image-review-fields"><input value={reviewIssues[task.id] ?? task.review_issues.join("、")} onChange={event => setReviewIssues(rows => ({ ...rows, [task.id]: event.target.value }))} placeholder="问题项，例如：珠子数量不符、流苏位置错误" /><textarea value={reviewComments[task.id] ?? task.review_comment} onChange={event => setReviewComments(rows => ({ ...rows, [task.id]: event.target.value }))} placeholder="修改意见或审核说明" /></div>
      <div><button type="button" className="human-secondary" disabled={!task.output_images.length} onClick={() => reviewTask(task, "approved")}>可用</button><button type="button" className="human-secondary" onClick={() => reviewTask(task, "need_redo")}>需重做</button><button type="button" className="human-secondary danger" onClick={() => reviewTask(task, "rejected")}>废弃</button>{["pending", "generating"].includes(task.status) && <button type="button" className="human-danger compact" onClick={() => controlTask(task, "terminate")}>终止任务</button>}{["failed", "cancelled"].includes(task.status) && <button type="button" className="human-secondary compact" onClick={() => controlTask(task, "retry")}>重试任务</button>}<button type="button" className="human-danger compact" onClick={() => setConfirmation({ title: "删除出图任务？", message: "将移除该任务及其关联的结果记录，无法恢复。", onConfirm: () => deleteTask(task) })}>删除任务</button></div>
    </article>)}
    {tasks.length === 0 && <p>暂无生成任务。先在出图方案里生成提示词并记录任务。</p>}
  </div>;
}
