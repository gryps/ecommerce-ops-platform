import type { ImageView } from "../../types";
import { ImageDelivery } from "./ImageDelivery";
import { ImageOverview } from "./ImageOverview";
import { ImagePlans } from "./ImagePlans";
import { ImageProductionHeader } from "./ImageProductionHeader";
import { ImageProducts } from "./ImageProducts";
import { ImageReview } from "./ImageReview";
import { ImageSourceGrouping } from "./ImageSourceGrouping";
import { useImageProductionController } from "./useImageProductionController";

export function ImageProduction({ view, onError, onNotice }: { view: ImageView; onError: (value: string) => void; onNotice: (value: string) => void }) {
  const {
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
  } = useImageProductionController({ onError, onNotice });
  if (view === "overview") {
    return <ImageOverview products={products} sourceAssets={sourceAssets} tasks={tasks} readyProducts={readyProducts} />;
  }
  if (view === "batches") {
    return <ImageSourceGrouping sourceAssets={sourceAssets} selectedSourceAssetIds={selectedSourceAssetIds} selectedProductName={selectedProductName} sourceAssetPreviewUrls={sourceAssetPreviewUrls} confirmation={confirmation} busy={busy} uploadingSourceAssets={uploadingSourceAssets} setSelectedSourceAssetIds={setSelectedSourceAssetIds} setSelectedProductName={setSelectedProductName} setConfirmation={setConfirmation} uploadSourceAssets={uploadSourceAssets} createProductFromSourceAssets={createProductFromSourceAssets} deleteSourceAsset={deleteSourceAsset} />;
  }
  return <section className="human-page image-production-page">
    <ImageProductionHeader view={view} />
    {view === "products" && <ImageProducts products={products} selected={selected} selectedProductIds={selectedProductIds} platformTemplateId={platformTemplateId} platformTemplates={platformTemplates} currentPlatformTemplate={currentPlatformTemplate} currentPlatformProfile={currentPlatformProfile} batchPlatformFieldKey={batchPlatformFieldKey} batchPlatformFieldValue={batchPlatformFieldValue} platformTemplateName={platformTemplateName} platformTemplatePlatform={platformTemplatePlatform} platformTemplateEntryUrl={platformTemplateEntryUrl} platformFields={platformFields} platformImageSlots={platformImageSlots} platformProfileValues={platformProfileValues} platformImageSelections={platformImageSelections} form={form} completion={completion} confirmation={confirmation} busy={busy} imageProductEditorRef={imageProductEditorRef} imageProductNameRef={imageProductNameRef} setSelectedId={setSelectedId} setSelectedProductIds={setSelectedProductIds} setPlatformTemplateId={setPlatformTemplateId} setBatchPlatformFieldKey={setBatchPlatformFieldKey} setBatchPlatformFieldValue={setBatchPlatformFieldValue} setPlatformTemplateName={setPlatformTemplateName} setPlatformTemplatePlatform={setPlatformTemplatePlatform} setPlatformTemplateEntryUrl={setPlatformTemplateEntryUrl} setPlatformFields={setPlatformFields} setPlatformImageSlots={setPlatformImageSlots} setPlatformProfileValues={setPlatformProfileValues} setConfirmation={setConfirmation} batchEditPlatformProfiles={batchEditPlatformProfiles} deleteImageProducts={deleteImageProducts} editImageProduct={editImageProduct} newPlatformTemplate={newPlatformTemplate} deletePlatformTemplate={deletePlatformTemplate} savePlatformTemplate={savePlatformTemplate} saveProduct={saveProduct} setForm={setForm} ensurePlatformProfile={ensurePlatformProfile} savePlatformProfile={savePlatformProfile} />}
    {view === "plans" && <ImagePlans products={products} selected={selected} selectedId={selectedId} templates={templates} currentTemplate={currentTemplate} templateId={templateId} model={model} outputPlan={outputPlan} prompt={prompt} busy={busy} setSelectedId={setSelectedId} setTemplateId={setTemplateId} setModel={setModel} setOutputPlan={setOutputPlan} setPrompt={setPrompt} generatePrompt={generatePrompt} createTaskFromPrompt={createTaskFromPrompt} />}
    {view === "review" && <ImageReview tasks={tasks} products={products} busy={busy} outputImageTypes={outputImageTypes} reviewIssues={reviewIssues} reviewComments={reviewComments} setOutputImageTypes={setOutputImageTypes} setReviewIssues={setReviewIssues} setReviewComments={setReviewComments} attachTaskOutputs={attachTaskOutputs} reviewTask={reviewTask} controlTask={controlTask} deleteTask={deleteTask} setConfirmation={setConfirmation} />}
    {view === "delivery" && <ImageDelivery products={products} selected={selected} selectedId={selectedId} platformTemplateId={platformTemplateId} platformTemplates={platformTemplates} currentPlatformTemplate={currentPlatformTemplate} currentPlatformProfile={currentPlatformProfile} tasks={tasks} platformImageSelections={platformImageSelections} platformProfileValues={platformProfileValues} platformUrl={platformUrl} browserSession={browserSession} confirmation={confirmation} busy={busy} setSelectedId={setSelectedId} setPlatformTemplateId={setPlatformTemplateId} setPlatformImageSelections={setPlatformImageSelections} setPlatformUrl={setPlatformUrl} setConfirmation={setConfirmation} ensurePlatformProfile={ensurePlatformProfile} savePlatformProfile={savePlatformProfile} startBrowserAutomation={startBrowserAutomation} stopBrowserAutomation={stopBrowserAutomation} />}
  </section>;
}
