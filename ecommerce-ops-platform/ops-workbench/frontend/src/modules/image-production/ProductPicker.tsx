import type { ImageProduct } from "../../types";

export function ProductPicker({ products, selectedId, onSelect }: { products: ImageProduct[]; selectedId: string; onSelect: (id: string) => void }) {
  const selected = selectedId ? products.find(item => item.id === selectedId) ?? null : null;

  return <aside className="human-card image-product-list">
    <div className="human-card-title"><h2>产品清单</h2><span>{products.length} 个产品</span></div>
    <div className="image-product-list-items">
      {products.map(product => <button type="button" key={product.id} className={selected?.id === product.id ? "active" : ""} onClick={() => onSelect(product.id)}>
        <b>{product.product_code}</b>
        <span>{product.name}</span>
        <small>{product.reference_count} 张实拍图</small>
      </button>)}
      {products.length === 0 && <p>还没有图片产品，请先在“拍摄分组”创建产品组。</p>}
    </div>
  </aside>;
}
