import { useState } from "react";
import { api } from "../../api";
import type { ImageProduct, ImageSourceAsset } from "../../types";
import { useSourceAssetPreviewUrls } from "./previewHooks";

type RunImageOperation = (work: () => Promise<unknown>, success: string) => Promise<boolean>;

export function useImageSourceAssets({
  sourceAssets,
  run,
  load,
  onError,
  onNotice,
  setSelectedId,
}: {
  sourceAssets: ImageSourceAsset[];
  run: RunImageOperation;
  load: () => Promise<void>;
  onError: (value: string) => void;
  onNotice: (value: string) => void;
  setSelectedId: (value: string) => void;
}) {
  const [selectedSourceAssetIds, setSelectedSourceAssetIds] = useState<string[]>([]);
  const [uploadingSourceAssets, setUploadingSourceAssets] = useState(false);
  const [selectedProductName, setSelectedProductName] = useState("");
  const sourceAssetPreviewUrls = useSourceAssetPreviewUrls(sourceAssets);

  async function uploadSourceAssets(files: FileList | null) {
    if (!files?.length) return;
    const body = new FormData();
    Array.from(files).forEach(file => body.append("images", file));
    setUploadingSourceAssets(true);
    onError("");
    onNotice("");
    try {
      const result = await api<{ items: ImageSourceAsset[] }>("/images/source-assets", { method: "POST", body });
      setSelectedSourceAssetIds(result.items.map(item => item.id));
      onNotice(`已上传 ${result.items.length} 张原始照片到素材库，已自动勾选待创建产品组。`);
      await load();
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "原始照片上传失败");
    } finally {
      setUploadingSourceAssets(false);
    }
  }

  async function deleteSourceAsset(asset: ImageSourceAsset) {
    await run(() => api(`/images/source-assets/${asset.id}`, { method: "DELETE" }), `已删除原始照片“${asset.name}”。`);
    setSelectedSourceAssetIds(ids => ids.filter(id => id !== asset.id));
  }

  async function createProductFromSourceAssets() {
    const productName = selectedProductName.trim();
    if (!selectedSourceAssetIds.length) {
      onError("请先从待分配素材中选择同一产品的原始照片。");
      return;
    }
    if (!productName) {
      onError("请填写产品名称后再创建产品组。");
      return;
    }
    await run(async () => {
      const result = await api<{ product: ImageProduct }>("/images/source-assets/create-product", { method: "POST", body: JSON.stringify({ name: productName, source_asset_ids: selectedSourceAssetIds }) });
      setSelectedId(result.product.id);
      setSelectedSourceAssetIds([]);
      setSelectedProductName("");
    }, `“${productName}”的产品组和产品档案已创建。`);
  }

  return {
    selectedSourceAssetIds,
    uploadingSourceAssets,
    selectedProductName,
    sourceAssetPreviewUrls,
    setSelectedSourceAssetIds,
    setSelectedProductName,
    uploadSourceAssets,
    deleteSourceAsset,
    createProductFromSourceAssets,
  };
}
