import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import type { OpsOverview, OpsProduct } from "../../types";

export type OpsProductForm = Omit<
  OpsProduct,
  "id" | "estimated_gross_profit_yuan" | "estimated_gross_margin" | "stock_warning" | "created_at" | "updated_at"
>;

const emptyProductForm: OpsProductForm = {
  product_code: "",
  name: "",
  category: "",
  style_tags: [],
  supplier_name: "",
  supplier_link: "",
  purchase_cost_yuan: 40,
  target_sale_price_yuan: 160,
  actual_sale_price_yuan: 160,
  stock_qty: 0,
  inbound_qty: 0,
  procurement_cycle_days: 7,
  status: "candidate",
  selection_grade: "",
  owner: "",
  notes: "",
};

export const OPS_STATUS_LABELS: Record<string, string> = {
  candidate: "候选",
  needs_sample: "待样品",
  ready_listing: "待上架",
  testing: "测试中",
  main: "主推",
  clearance: "清仓",
  retired: "淘汰",
};

export const OPS_GRADE_LABELS = ["", "A", "B", "C", "D"];

export function useOperationsData({
  onError,
  onNotice,
}: {
  onError: (value: string) => void;
  onNotice: (value: string) => void;
}) {
  const [overview, setOverview] = useState<OpsOverview | null>(null);
  const [products, setProducts] = useState<OpsProduct[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState<OpsProductForm>(emptyProductForm);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setBusy(true);
    onError("");
    try {
      const [overviewRows, productRows] = await Promise.all([
        api<OpsOverview>("/operations/overview"),
        api<OpsProduct[]>("/operations/products"),
      ]);
      setOverview(overviewRows);
      setProducts(productRows);
      if (!selectedId && productRows.length) setSelectedId(productRows[0].id);
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "运营中心数据加载失败");
    } finally {
      setBusy(false);
    }
  }, [onError, selectedId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const selected = useMemo(() => products.find(item => item.id === selectedId) ?? null, [products, selectedId]);

  useEffect(() => {
    if (!selected) return;
    setForm({
      product_code: selected.product_code,
      name: selected.name,
      category: selected.category,
      style_tags: selected.style_tags,
      supplier_name: selected.supplier_name,
      supplier_link: selected.supplier_link,
      purchase_cost_yuan: selected.purchase_cost_yuan,
      target_sale_price_yuan: selected.target_sale_price_yuan,
      actual_sale_price_yuan: selected.actual_sale_price_yuan,
      stock_qty: selected.stock_qty,
      inbound_qty: selected.inbound_qty,
      procurement_cycle_days: selected.procurement_cycle_days,
      status: selected.status,
      selection_grade: selected.selection_grade,
      owner: selected.owner,
      notes: selected.notes,
    });
  }, [selected]);

  const newProduct = useCallback(() => {
    setSelectedId("");
    setForm(emptyProductForm);
  }, []);

  const saveProduct = useCallback(async () => {
    setBusy(true);
    onError("");
    onNotice("");
    try {
      const payload = { ...form, style_tags: form.style_tags.filter(Boolean) };
      const saved = selectedId
        ? await api<OpsProduct>(`/operations/products/${selectedId}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await api<OpsProduct>("/operations/products", { method: "POST", body: JSON.stringify(payload) });
      onNotice(selectedId ? "运营商品已更新" : "运营商品已创建");
      setSelectedId(saved.id);
      await reload();
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "运营商品保存失败");
    } finally {
      setBusy(false);
    }
  }, [form, onError, onNotice, reload, selectedId]);

  return {
    overview,
    products,
    selected,
    selectedId,
    form,
    busy,
    setSelectedId,
    setForm,
    newProduct,
    saveProduct,
    reload,
  };
}
