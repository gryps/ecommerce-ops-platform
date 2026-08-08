import { FormEvent, useState } from "react";
import { api } from "../../api";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import type { DeleteConfirmation, Product } from "../../types";
import { fuzzyRows } from "../../utils/fuzzy";

export function ProductManager({ products, act }: {
  products: Product[];
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
}) {
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [page, setPage] = useState(0);
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const activeProducts = products.filter(item => item.status === "active");
  const visibleProducts = activeProducts;
  const pageProducts = visibleProducts.slice(page * 20, page * 20 + 20);

  async function create(event: FormEvent) {
    event.preventDefault();
    const nextName = name.trim();
    if (!nextName) return;
    await act(
      () => api("/products", { method: "POST", body: JSON.stringify({ name: nextName }) }),
      "产品名称已添加",
    );
    setName("");
  }

  async function saveName(product: Product) {
    const nextName = editingName.trim();
    if (!nextName || nextName === product.name) { setEditingId(null); return; }
    await act(
      () => api(`/products/${product.id}`, { method: "PATCH", body: JSON.stringify({ name: nextName }) }),
      "产品名称已更新",
    );
    setEditingId(null);
  }

  return <div className="human-card product-library-card">
      <div className="human-card-title"><h2>产品名称</h2><span>用于素材归类文件夹、文件名及剪映草稿归属</span></div>
      <div className="product-manager product-library-manager">
        <div className="product-manager-heading"><b>新增产品名称</b><span>名称不可重复，后续可以修改</span></div>
        <form onSubmit={create}>
          <input list="master-product-hints" value={name} onChange={event => setName(event.target.value)} placeholder="输入新名称或模糊查询已有产品" maxLength={160} required /><datalist id="master-product-hints">{fuzzyRows(activeProducts, name, item => item.name).map(item => <option key={item.id} value={item.name} />)}</datalist>
          <button>添加产品</button>
        </form>
      </div>
      <div className="product-library-summary">
        <span>共 {visibleProducts.length} 个产品</span>
      </div>
      <div className="product-manager-list product-library-list">
        {pageProducts.map(product => <div key={product.id}>
          <span>
            {editingId === product.id
              ? <input autoFocus value={editingName} maxLength={160} onChange={event => setEditingName(event.target.value)} onKeyDown={event => {
                if (event.key === "Escape") setEditingId(null);
                if (event.key === "Enter") { event.preventDefault(); saveName(product); }
              }} />
              : <b>{product.name || "未命名产品"}</b>}
            <small>{product.system_code} · {product.asset_count} 条素材</small>
          </span>
          <div>
            {editingId === product.id ? <>
              <button type="button" onClick={() => saveName(product)}>保存</button>
              <button type="button" className="human-secondary" onClick={() => setEditingId(null)}>取消</button>
            </> : <button type="button" className="human-secondary" onClick={() => { setEditingId(product.id); setEditingName(product.name); }}>改名</button>}
            <button type="button" className="human-secondary danger" onClick={() => setConfirmation({ title: `删除产品“${product.name || product.system_code}”？`, message: "将删除产品及其数据库关联，磁盘上的视频不会移动或改名。", onConfirm: async () => { await act(() => api(`/human/products/${product.id}`, { method: "DELETE" }), "产品已删除"); } })}>删除</button>
          </div>
        </div>)}
        {visibleProducts.length === 0 && <div className="product-library-empty">还没有产品名称，请先添加一个。</div>}
      </div>
      {visibleProducts.length > 20 && <div className="resource-pagination"><button className="human-secondary" disabled={page === 0} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page + 1} / {Math.ceil(visibleProducts.length / 20)}</span><button className="human-secondary" disabled={(page + 1) * 20 >= visibleProducts.length} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
      <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
  </div>;
}
