import { useEffect, useState } from "react";
import { api } from "../../api";
import type { ImageProduct, PlatformField, PlatformImageSlot, PlatformProfile, PlatformTemplate } from "../../types";

type RunImageOperation = (work: () => Promise<unknown>, success: string) => Promise<boolean>;

export function usePlatformTemplateEditor({
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
}: {
  selected: ImageProduct | null;
  currentPlatformTemplate: PlatformTemplate | null;
  currentPlatformProfile: PlatformProfile | null;
  platformTemplateId: string;
  selectedProductIds: string[];
  batchPlatformFieldKey: string;
  batchPlatformFieldValue: string;
  run: RunImageOperation;
  onError: (value: string) => void;
  setPlatformTemplateId: (value: string) => void;
}) {
  const [platformTemplateName, setPlatformTemplateName] = useState("");
  const [platformTemplatePlatform, setPlatformTemplatePlatform] = useState("");
  const [platformTemplateEntryUrl, setPlatformTemplateEntryUrl] = useState("");
  const [platformFields, setPlatformFields] = useState<PlatformField[]>([]);
  const [platformImageSlots, setPlatformImageSlots] = useState<PlatformImageSlot[]>([]);
  const [platformProfileValues, setPlatformProfileValues] = useState<Record<string, unknown>>({});
  const [platformImageSelections, setPlatformImageSelections] = useState<PlatformProfile["image_selections"]>({});

  useEffect(() => {
    if (!currentPlatformTemplate) {
      setPlatformTemplateName("");
      setPlatformTemplatePlatform("");
      setPlatformTemplateEntryUrl("");
      setPlatformFields([]);
      setPlatformImageSlots([]);
      return;
    }
    setPlatformTemplateName(currentPlatformTemplate.name);
    setPlatformTemplatePlatform(currentPlatformTemplate.platform);
    setPlatformTemplateEntryUrl(currentPlatformTemplate.entry_url);
    setPlatformFields(currentPlatformTemplate.fields);
    setPlatformImageSlots(currentPlatformTemplate.image_slots);
  }, [currentPlatformTemplate?.id]);

  useEffect(() => {
    setPlatformProfileValues(currentPlatformProfile?.values ?? {});
    setPlatformImageSelections(currentPlatformProfile?.image_selections ?? {});
  }, [currentPlatformProfile?.id]);

  const templatePayload = () => ({
    name: platformTemplateName,
    platform: platformTemplatePlatform,
    entry_url: platformTemplateEntryUrl,
    fields: platformFields,
    image_slots: platformImageSlots,
  });

  async function savePlatformTemplate() {
    if (!platformTemplateName.trim()) {
      onError("请填写平台模板名称");
      return;
    }
    let savedId = platformTemplateId;
    await run(() => (platformTemplateId
      ? api<PlatformTemplate>(`/images/platform-templates/${platformTemplateId}`, { method: "PATCH", body: JSON.stringify(templatePayload()) })
      : api<PlatformTemplate>("/images/platform-templates", { method: "POST", body: JSON.stringify(templatePayload()) })
    ).then(item => { savedId = item.id; }), "平台模板已保存；已有产品档案会保留原值，新增字段需要补充。");
    if (savedId) setPlatformTemplateId(savedId);
  }

  function newPlatformTemplate() {
    setPlatformTemplateId("");
    setPlatformTemplateName("");
    setPlatformTemplatePlatform("");
    setPlatformTemplateEntryUrl("");
    setPlatformFields([]);
    setPlatformImageSlots([]);
  }

  async function ensurePlatformProfile() {
    if (!selected || !platformTemplateId) {
      onError("请先选择产品和平台模板");
      return;
    }
    await run(() => api(`/images/products/${selected.id}/platform-profiles/${platformTemplateId}`, { method: "POST" }), "已创建该平台的产品档案，请填写字段并选择图片。");
  }

  async function savePlatformProfile(values: Record<string, unknown>, imageSelections: PlatformProfile["image_selections"]) {
    if (!currentPlatformProfile) return;
    await run(() => api(`/images/platform-profiles/${currentPlatformProfile.id}`, { method: "PATCH", body: JSON.stringify({ values, image_selections: imageSelections }) }), "平台产品档案已保存。");
  }

  async function deletePlatformTemplate() {
    if (!platformTemplateId) return;
    await run(() => api(`/images/platform-templates/${platformTemplateId}`, { method: "DELETE" }), "平台模板及其平台档案已删除。");
    setPlatformTemplateId("");
    newPlatformTemplate();
  }

  async function batchEditPlatformProfiles() {
    if (!selectedProductIds.length || !currentPlatformTemplate || !batchPlatformFieldKey) {
      onError("请先勾选产品、选择平台模板和自定义字段。");
      return;
    }
    await run(() => api("/images/platform-profile-batch-fields", { method: "PATCH", body: JSON.stringify({ product_ids: selectedProductIds, template_id: currentPlatformTemplate.id, values: { [batchPlatformFieldKey]: batchPlatformFieldValue } }) }), `已按“${currentPlatformTemplate.name}”批量更新 ${selectedProductIds.length} 个产品的自定义字段。`);
  }

  return {
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
  };
}
