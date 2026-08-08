import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import type { ImageProduct, ImageSourceAsset, ImageTask, ImageTemplate, PlatformProfile, PlatformTemplate } from "../../types";

export function useImageProductionData({
  selectedId,
  templateId,
  platformTemplateId,
  setSelectedId,
  setTemplateId,
  setPlatformTemplateId,
  setBusy,
  onError,
}: {
  selectedId: string;
  templateId: string;
  platformTemplateId: string;
  setSelectedId: (value: string) => void;
  setTemplateId: (value: string) => void;
  setPlatformTemplateId: (value: string) => void;
  setBusy: (value: boolean) => void;
  onError: (value: string) => void;
}) {
  const [products, setProducts] = useState<ImageProduct[]>([]);
  const [templates, setTemplates] = useState<ImageTemplate[]>([]);
  const [tasks, setTasks] = useState<ImageTask[]>([]);
  const [sourceAssets, setSourceAssets] = useState<ImageSourceAsset[]>([]);
  const [platformTemplates, setPlatformTemplates] = useState<PlatformTemplate[]>([]);
  const [platformProfiles, setPlatformProfiles] = useState<PlatformProfile[]>([]);

  const load = useCallback(async () => {
    setBusy(true);
    onError("");
    try {
      const [productRows, templateRows, taskRows, sourceAssetRows, platformTemplateRows, platformProfileRows] = await Promise.all([
        api<{ items: ImageProduct[] }>("/images/products"),
        api<{ items: ImageTemplate[] }>("/images/templates"),
        api<{ items: ImageTask[] }>("/images/tasks"),
        api<{ items: ImageSourceAsset[] }>("/images/source-assets"),
        api<{ items: PlatformTemplate[] }>("/images/platform-templates"),
        api<{ items: PlatformProfile[] }>("/images/platform-profiles"),
      ]);
      setProducts(productRows.items);
      setTemplates(templateRows.items);
      setTasks(taskRows.items);
      setSourceAssets(sourceAssetRows.items);
      setPlatformTemplates(platformTemplateRows.items);
      setPlatformProfiles(platformProfileRows.items);
      if (!selectedId && productRows.items[0]) setSelectedId(productRows.items[0].id);
      if (!templateId && templateRows.items[0]) setTemplateId(templateRows.items[0].id);
      if (!platformTemplateId && platformTemplateRows.items[0]) setPlatformTemplateId(platformTemplateRows.items[0].id);
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "图片生产数据加载失败");
    } finally {
      setBusy(false);
    }
  }, [onError, platformTemplateId, selectedId, setBusy, setPlatformTemplateId, setSelectedId, setTemplateId, templateId]);

  useEffect(() => {
    load();
  }, [load]);

  return {
    products,
    templates,
    tasks,
    sourceAssets,
    platformTemplates,
    platformProfiles,
    load,
  };
}
