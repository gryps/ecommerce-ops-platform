import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import type { ImagePrompt, ImageProduct } from "../../types";

type RunImageOperation = (work: () => Promise<unknown>, success: string) => Promise<boolean>;

export function useImageProductEditor({
  selected,
  selectedId,
  setSelectedId,
  setSelectedProductIds,
  setPrompt,
  run,
}: {
  selected: ImageProduct | null;
  selectedId: string;
  setSelectedId: (value: string) => void;
  setSelectedProductIds: (setter: (current: string[]) => string[]) => void;
  setPrompt: (value: ImagePrompt | null) => void;
  run: RunImageOperation;
}) {
  const emptyForm = { product_code: "", name: "" };
  const [form, setForm] = useState(emptyForm);
  const imageProductEditorRef = useRef<HTMLDivElement | null>(null);
  const imageProductNameRef = useRef<HTMLInputElement | null>(null);
  const shouldFocusImageProductEditor = useRef(false);

  useEffect(() => {
    if (!selected) {
      setForm(emptyForm);
      return;
    }
    setForm({ product_code: selected.product_code, name: selected.name });
    setPrompt(null);
    if (shouldFocusImageProductEditor.current) {
      shouldFocusImageProductEditor.current = false;
      window.requestAnimationFrame(() => {
        imageProductEditorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        imageProductNameRef.current?.focus();
      });
    }
  }, [selected?.id]);

  const payload = () => ({ product_code: form.product_code, name: form.name });

  async function saveProduct(event: FormEvent) {
    event.preventDefault();
    const data = payload();
    if (!data.product_code.trim() || !data.name.trim()) return;
    if (selected) {
      await run(() => api(`/images/products/${selected.id}`, { method: "PATCH", body: JSON.stringify(data) }), "产品档案已保存");
    } else {
      let createdId = "";
      await run(() => api<ImageProduct>("/images/products", { method: "POST", body: JSON.stringify(data) }).then(value => { createdId = value.id; }), "产品档案已创建");
      if (createdId) setSelectedId(createdId);
    }
  }

  function editImageProduct(productId: string) {
    shouldFocusImageProductEditor.current = true;
    setSelectedId(productId);
    if (selectedId === productId) {
      shouldFocusImageProductEditor.current = false;
      window.requestAnimationFrame(() => {
        imageProductEditorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        imageProductNameRef.current?.focus();
      });
    }
  }

  async function deleteImageProducts(productIds: string[], deleteSourceAssets = false) {
    const ids = [...new Set(productIds)];
    if (!ids.length) return false;
    const succeeded = await run(async () => {
      const suffix = deleteSourceAssets ? "?delete_source_assets=true" : "";
      for (const productId of ids) await api(`/images/products/${productId}${suffix}`, { method: "DELETE" });
      setSelectedProductIds(current => current.filter(id => !ids.includes(id)));
      if (selectedId && ids.includes(selectedId)) setSelectedId("");
    }, deleteSourceAssets ? `已删除 ${ids.length} 个产品条目及其原始照片。` : `已删除 ${ids.length} 个产品条目，原始照片已退回待分配区。`);
    return succeeded;
  }

  return {
    form,
    imageProductEditorRef,
    imageProductNameRef,
    setForm,
    saveProduct,
    editImageProduct,
    deleteImageProducts,
  };
}
