import { useImageProductionData } from "./useImageProductionData";
import { useImageProductEditor } from "./useImageProductEditor";
import { useImageSourceAssets } from "./useImageSourceAssets";
import { useImageTaskActions } from "./useImageTaskActions";
import { useImageProductionUiState } from "./useImageProductionUiState";
import { usePlatformBrowserSession } from "./usePlatformBrowserSession";
import { usePlatformTemplateEditor } from "./usePlatformTemplateEditor";

export function useImageProductionController({
  onError,
  onNotice,
}: {
  onError: (value: string) => void;
  onNotice: (value: string) => void;
}) {
  const ui = useImageProductionUiState();
  const { platformUrl, browserSession, setPlatformUrl, startBrowserAutomation, stopBrowserAutomation } = usePlatformBrowserSession({ onError, onNotice });
  const { products, templates, tasks, sourceAssets, platformTemplates, platformProfiles, load } = useImageProductionData({
    selectedId: ui.selectedId,
    templateId: ui.templateId,
    platformTemplateId: ui.platformTemplateId,
    setSelectedId: ui.setSelectedId,
    setTemplateId: ui.setTemplateId,
    setPlatformTemplateId: ui.setPlatformTemplateId,
    setBusy: ui.setBusy,
    onError,
  });

  const selected = ui.selectedId ? products.find(item => item.id === ui.selectedId) ?? null : null;
  const currentTemplate = templates.find(item => item.id === ui.templateId) ?? templates[0] ?? null;
  const currentPlatformTemplate = platformTemplates.find(item => item.id === ui.platformTemplateId) ?? null;
  const currentPlatformProfile = platformProfiles.find(item => item.product_id === selected?.id && item.template_id === ui.platformTemplateId) ?? null;
  const readyProducts = products.filter(item => item.reference_count > 0);
  const completion = selected && selected.reference_total > 0 ? Math.round((selected.reference_count / selected.reference_total) * 100) : 0;

  async function run(work: () => Promise<unknown>, success: string) {
    ui.setBusy(true);
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
      ui.setBusy(false);
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
    selectedId: ui.selectedId,
    setSelectedId: ui.setSelectedId,
    setSelectedProductIds: ui.setSelectedProductIds,
    setPrompt: ui.setPrompt,
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
    platformTemplateId: ui.platformTemplateId,
    selectedProductIds: ui.selectedProductIds,
    batchPlatformFieldKey: ui.batchPlatformFieldKey,
    batchPlatformFieldValue: ui.batchPlatformFieldValue,
    run,
    onError,
    setPlatformTemplateId: ui.setPlatformTemplateId,
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
    setSelectedId: ui.setSelectedId,
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
    model: ui.model,
    outputPlan: ui.outputPlan,
    reviewIssues: ui.reviewIssues,
    reviewComments: ui.reviewComments,
    outputImageTypes: ui.outputImageTypes,
    setPrompt: ui.setPrompt,
    run,
  });

  return {
    products,
    templates,
    tasks,
    platformTemplates,
    platformTemplateId: ui.platformTemplateId,
    platformTemplateName,
    platformTemplatePlatform,
    platformTemplateEntryUrl,
    platformFields,
    platformImageSlots,
    platformProfileValues,
    platformImageSelections,
    selectedId: ui.selectedId,
    templateId: ui.templateId,
    model: ui.model,
    outputPlan: ui.outputPlan,
    prompt: ui.prompt,
    form,
    sourceAssets,
    selectedSourceAssetIds,
    uploadingSourceAssets,
    selectedProductName,
    selectedProductIds: ui.selectedProductIds,
    confirmation: ui.confirmation,
    batchPlatformFieldKey: ui.batchPlatformFieldKey,
    batchPlatformFieldValue: ui.batchPlatformFieldValue,
    reviewIssues: ui.reviewIssues,
    reviewComments: ui.reviewComments,
    outputImageTypes: ui.outputImageTypes,
    platformUrl,
    browserSession,
    busy: ui.busy,
    imageProductEditorRef,
    imageProductNameRef,
    selected,
    currentTemplate,
    currentPlatformTemplate,
    currentPlatformProfile,
    sourceAssetPreviewUrls,
    readyProducts,
    completion,
    setPlatformTemplateId: ui.setPlatformTemplateId,
    setPlatformTemplateName,
    setPlatformTemplatePlatform,
    setPlatformTemplateEntryUrl,
    setPlatformFields,
    setPlatformImageSlots,
    setPlatformProfileValues,
    setPlatformImageSelections,
    setSelectedId: ui.setSelectedId,
    setTemplateId: ui.setTemplateId,
    setModel: ui.setModel,
    setOutputPlan: ui.setOutputPlan,
    setPrompt: ui.setPrompt,
    setForm,
    setSelectedSourceAssetIds,
    setSelectedProductName,
    setSelectedProductIds: ui.setSelectedProductIds,
    setConfirmation: ui.setConfirmation,
    setBatchPlatformFieldKey: ui.setBatchPlatformFieldKey,
    setBatchPlatformFieldValue: ui.setBatchPlatformFieldValue,
    setReviewIssues: ui.setReviewIssues,
    setReviewComments: ui.setReviewComments,
    setOutputImageTypes: ui.setOutputImageTypes,
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
