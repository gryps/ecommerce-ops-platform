import { useState } from "react";
import type {
  DeleteConfirmation,
  ImagePrompt,
} from "../../types";
import { useImageProductionData } from "./useImageProductionData";
import { useImageProductEditor } from "./useImageProductEditor";
import { useImageSourceAssets } from "./useImageSourceAssets";
import { useImageTaskActions } from "./useImageTaskActions";
import { usePlatformBrowserSession } from "./usePlatformBrowserSession";
import { usePlatformTemplateEditor } from "./usePlatformTemplateEditor";

export function useImageProductionController({
  onError,
  onNotice,
}: {
  onError: (value: string) => void;
  onNotice: (value: string) => void;
}) {
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
  const { platformUrl, browserSession, setPlatformUrl, startBrowserAutomation, stopBrowserAutomation } = usePlatformBrowserSession({ onError, onNotice });
  const { products, templates, tasks, sourceAssets, platformTemplates, platformProfiles, load } = useImageProductionData({
    selectedId,
    templateId,
    platformTemplateId,
    setSelectedId,
    setTemplateId,
    setPlatformTemplateId,
    setBusy,
    onError,
  });

  const selected = selectedId ? products.find(item => item.id === selectedId) ?? null : null;
  const currentTemplate = templates.find(item => item.id === templateId) ?? templates[0] ?? null;
  const currentPlatformTemplate = platformTemplates.find(item => item.id === platformTemplateId) ?? null;
  const currentPlatformProfile = platformProfiles.find(item => item.product_id === selected?.id && item.template_id === platformTemplateId) ?? null;
  const readyProducts = products.filter(item => item.reference_count > 0);
  const completion = selected && selected.reference_total > 0 ? Math.round((selected.reference_count / selected.reference_total) * 100) : 0;

  async function run(work: () => Promise<unknown>, success: string) {
    setBusy(true);
    onError("");
    onNotice("");
    try {
      await work();
      onNotice(success);
      await load();
      return true;
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "操作失败");
      return false;
    } finally {
      setBusy(false);
    }
  }

  const {
    form,
    imageProductEditorRef,
    imageProductNameRef,
    setForm,
    saveProduct,
    editImageProduct,
    deleteImageProducts,
  } = useImageProductEditor({
    selected,
    selectedId,
    setSelectedId,
    setSelectedProductIds,
    setPrompt,
    run,
  });

  const {
    platformTemplateName,
    platformTemplatePlatform,
    platformTemplateEntryUrl,
    platformFields,
    platformImageSlots,
    platformProfileValues,
    platformImageSelections,
    setPlatformTemplateName,
    setPlatformTemplatePlatform,
    setPlatformTemplateEntryUrl,
    setPlatformFields,
    setPlatformImageSlots,
    setPlatformProfileValues,
    setPlatformImageSelections,
    savePlatformTemplate,
    newPlatformTemplate,
    ensurePlatformProfile,
    savePlatformProfile,
    deletePlatformTemplate,
    batchEditPlatformProfiles,
  } = usePlatformTemplateEditor({
    selected,
    currentPlatformTemplate,
    currentPlatformProfile,
    platformTemplateId,
    selectedProductIds,
    batchPlatformFieldKey,
    batchPlatformFieldValue,
    run,
    onError,
    setPlatformTemplateId,
  });

  const {
    selectedSourceAssetIds,
    uploadingSourceAssets,
    selectedProductName,
    sourceAssetPreviewUrls,
    setSelectedSourceAssetIds,
    setSelectedProductName,
    uploadSourceAssets,
    deleteSourceAsset,
    createProductFromSourceAssets,
  } = useImageSourceAssets({
    sourceAssets,
    run,
    load,
    onError,
    onNotice,
    setSelectedId,
  });

  const {
    generatePrompt,
    createTaskFromPrompt,
    reviewTask,
    controlTask,
    deleteTask,
    attachTaskOutputs,
  } = useImageTaskActions({
    selected,
    currentTemplate,
    model,
    outputPlan,
    reviewIssues,
    reviewComments,
    outputImageTypes,
    setPrompt,
    run,
  });

  return {
    products,
    templates,
    tasks,
    platformTemplates,
    platformTemplateId,
    platformTemplateName,
    platformTemplatePlatform,
    platformTemplateEntryUrl,
    platformFields,
    platformImageSlots,
    platformProfileValues,
    platformImageSelections,
    selectedId,
    templateId,
    model,
    outputPlan,
    prompt,
    form,
    sourceAssets,
    selectedSourceAssetIds,
    uploadingSourceAssets,
    selectedProductName,
    selectedProductIds,
    confirmation,
    batchPlatformFieldKey,
    batchPlatformFieldValue,
    reviewIssues,
    reviewComments,
    outputImageTypes,
    platformUrl,
    browserSession,
    busy,
    imageProductEditorRef,
    imageProductNameRef,
    selected,
    currentTemplate,
    currentPlatformTemplate,
    currentPlatformProfile,
    sourceAssetPreviewUrls,
    readyProducts,
    completion,
    setPlatformTemplateId,
    setPlatformTemplateName,
    setPlatformTemplatePlatform,
    setPlatformTemplateEntryUrl,
    setPlatformFields,
    setPlatformImageSlots,
    setPlatformProfileValues,
    setPlatformImageSelections,
    setSelectedId,
    setTemplateId,
    setModel,
    setOutputPlan,
    setPrompt,
    setForm,
    setSelectedSourceAssetIds,
    setSelectedProductName,
    setSelectedProductIds,
    setConfirmation,
    setBatchPlatformFieldKey,
    setBatchPlatformFieldValue,
    setReviewIssues,
    setReviewComments,
    setOutputImageTypes,
    setPlatformUrl,
    saveProduct,
    editImageProduct,
    generatePrompt,
    createTaskFromPrompt,
    reviewTask,
    controlTask,
    deleteTask,
    attachTaskOutputs,
    savePlatformTemplate,
    newPlatformTemplate,
    ensurePlatformProfile,
    savePlatformProfile,
    deletePlatformTemplate,
    startBrowserAutomation,
    stopBrowserAutomation,
    uploadSourceAssets,
    deleteSourceAsset,
    createProductFromSourceAssets,
    batchEditPlatformProfiles,
    deleteImageProducts,
  };
}
