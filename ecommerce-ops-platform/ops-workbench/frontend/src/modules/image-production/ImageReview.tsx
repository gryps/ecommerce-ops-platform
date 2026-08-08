import type { Dispatch, SetStateAction } from "react";
import type { DeleteConfirmation, ImageProduct, ImageTask } from "../../types";
import { ImageTaskList } from "./ImageTaskList";

export function ImageReview({
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
  const reviewedTasks = tasks.filter(item => item.review_status === "approved");
  const redoTasks = tasks.filter(item => item.review_status === "need_redo");

  return <div className="image-review-layout">
    <div className="human-metrics">
      <article><b>{tasks.length}</b><span>全部出图任务</span></article>
      <article><b>{reviewedTasks.length}</b><span>已标记可用</span></article>
      <article><b>{redoTasks.length}</b><span>需重做</span></article>
      <article><b>{tasks.filter(item => item.review_status === "rejected").length}</b><span>已废弃</span></article>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>结果审核队列</h2><span>按产品查看白底图、环境搭配图、佩戴图、商详图</span></div><ImageTaskList tasks={tasks} products={products} busy={busy} outputImageTypes={outputImageTypes} reviewIssues={reviewIssues} reviewComments={reviewComments} setOutputImageTypes={setOutputImageTypes} setReviewIssues={setReviewIssues} setReviewComments={setReviewComments} attachTaskOutputs={attachTaskOutputs} reviewTask={reviewTask} controlTask={controlTask} deleteTask={deleteTask} setConfirmation={setConfirmation} /></div>
  </div>;
}
