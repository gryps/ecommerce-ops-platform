import { useEffect, useState } from "react";
import { apiBlob } from "../../api";
import type { ImageSourceAsset } from "../../types";

export function useSourceAssetPreviewUrls(sourceAssets: ImageSourceAsset[]) {
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    const urls: string[] = [];
    const queue = sourceAssets.filter(asset => asset.status === "unassigned").slice(0, 120);
    setPreviewUrls({});

    async function loadPreviews() {
      await Promise.all(Array.from({ length: Math.min(6, queue.length) }, async () => {
        while (!cancelled && queue.length) {
          const asset = queue.shift();
          if (!asset) return;
          try {
            const url = URL.createObjectURL(await apiBlob(`/images/source-assets/${asset.id}/file`));
            urls.push(url);
            if (!cancelled) setPreviewUrls(current => ({ ...current, [asset.id]: url }));
          } catch {
            // 文件异常时仍可显示名称与删除操作。
          }
        }
      }));
    }

    void loadPreviews();
    return () => {
      cancelled = true;
      urls.forEach(url => URL.revokeObjectURL(url));
    };
  }, [sourceAssets]);

  return previewUrls;
}
