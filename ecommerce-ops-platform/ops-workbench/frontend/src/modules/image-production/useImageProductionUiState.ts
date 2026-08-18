import { useState } from "react";
import type { DeleteConfirmation, ImagePrompt } from "../../types";

export function useImageProductionUiState() {
  const [platformTemplateId, setPlatformTemplateId] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [model, setModel] = useState("");
  const [outputPlan, setOutputPlan] = useState<Record<string, number>>({ "白底图": 2, "环境搭配图": 2, "佩戴图": 2, "商详图": 4 });
  const [prompt, setPrompt] = useState<ImagePrompt | null>(null);
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const [batchPlatformFieldKey, setBatchPlatformFieldKey] = useState("");
  const [batchPlatformFieldValue, setBatchPlatformFieldValue] = useState("");
  const [reviewIssues, setReviewIssues] = useState<Record<string, string>>({});
  const [reviewComments, setReviewComments] = useState<Record<string, string>>({});
  const [outputImageTypes, setOutputImageTypes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  return {
    platformTemplateId,
    selectedId,
    templateId,
    model,
    outputPlan,
    prompt,
    selectedProductIds,
    confirmation,
    batchPlatformFieldKey,
    batchPlatformFieldValue,
    reviewIssues,
    reviewComments,
    outputImageTypes,
    busy,
    setPlatformTemplateId,
    setSelectedId,
    setTemplateId,
    setModel,
    setOutputPlan,
    setPrompt,
    setSelectedProductIds,
    setConfirmation,
    setBatchPlatformFieldKey,
    setBatchPlatformFieldValue,
    setReviewIssues,
    setReviewComments,
    setOutputImageTypes,
    setBusy,
  };
}
