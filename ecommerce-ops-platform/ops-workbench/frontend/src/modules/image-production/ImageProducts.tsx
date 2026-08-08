import type { Dispatch, FormEvent, RefObject, SetStateAction } from "react";
import { LoaderCircle } from "lucide-react";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import { Pill } from "../../components/Pill";
import type { DeleteConfirmation, ImageProduct, PlatformField, PlatformImageSlot, PlatformProfile, PlatformTemplate } from "../../types";
import { PlatformTemplateManager } from "./PlatformTemplateManager";

type ProductForm = { product_code: string; name: string };

export function ImageProducts({
  products,
  selected,
  selectedProductIds,
  platformTemplateId,
  platformTemplates,
  currentPlatformTemplate,
  currentPlatformProfile,
  batchPlatformFieldKey,
  batchPlatformFieldValue,
  platformTemplateName,
  platformTemplatePlatform,
  platformTemplateEntryUrl,
  platformFields,
  platformImageSlots,
  platformProfileValues,
  platformImageSelections,
  form,
  completion,
  confirmation,
  busy,
  imageProductEditorRef,
  imageProductNameRef,
  setSelectedId,
  setSelectedProductIds,
  setPlatformTemplateId,
  setBatchPlatformFieldKey,
  setBatchPlatformFieldValue,
  setPlatformTemplateName,
  setPlatformTemplatePlatform,
  setPlatformTemplateEntryUrl,
  setPlatformFields,
  setPlatformImageSlots,
  setPlatformProfileValues,
  setConfirmation,
  batchEditPlatformProfiles,
  deleteImageProducts,
  editImageProduct,
  newPlatformTemplate,
  deletePlatformTemplate,
  savePlatformTemplate,
  saveProduct,
  setForm,
  ensurePlatformProfile,
  savePlatformProfile,
}: {
  products: ImageProduct[];
  selected: ImageProduct | null;
  selectedProductIds: string[];
  platformTemplateId: string;
  platformTemplates: PlatformTemplate[];
  currentPlatformTemplate: PlatformTemplate | null;
  currentPlatformProfile: PlatformProfile | null;
  batchPlatformFieldKey: string;
  batchPlatformFieldValue: string;
  platformTemplateName: string;
  platformTemplatePlatform: string;
  platformTemplateEntryUrl: string;
  platformFields: PlatformField[];
  platformImageSlots: PlatformImageSlot[];
  platformProfileValues: Record<string, unknown>;
  platformImageSelections: PlatformProfile["image_selections"];
  form: ProductForm;
  completion: number;
  confirmation: DeleteConfirmation | null;
  busy: boolean;
  imageProductEditorRef: RefObject<HTMLDivElement | null>;
  imageProductNameRef: RefObject<HTMLInputElement | null>;
  setSelectedId: Dispatch<SetStateAction<string>>;
  setSelectedProductIds: Dispatch<SetStateAction<string[]>>;
  setPlatformTemplateId: Dispatch<SetStateAction<string>>;
  setBatchPlatformFieldKey: Dispatch<SetStateAction<string>>;
  setBatchPlatformFieldValue: Dispatch<SetStateAction<string>>;
  setPlatformTemplateName: Dispatch<SetStateAction<string>>;
  setPlatformTemplatePlatform: Dispatch<SetStateAction<string>>;
  setPlatformTemplateEntryUrl: Dispatch<SetStateAction<string>>;
  setPlatformFields: Dispatch<SetStateAction<PlatformField[]>>;
  setPlatformImageSlots: Dispatch<SetStateAction<PlatformImageSlot[]>>;
  setPlatformProfileValues: Dispatch<SetStateAction<Record<string, unknown>>>;
  setConfirmation: Dispatch<SetStateAction<DeleteConfirmation | null>>;
  batchEditPlatformProfiles: () => Promise<void>;
  deleteImageProducts: (productIds: string[], deleteSourceAssets?: boolean) => Promise<boolean>;
  editImageProduct: (productId: string) => void;
  newPlatformTemplate: () => void;
  deletePlatformTemplate: () => Promise<void>;
  savePlatformTemplate: () => Promise<void>;
  saveProduct: (event: FormEvent) => Promise<void>;
  setForm: Dispatch<SetStateAction<ProductForm>>;
  ensurePlatformProfile: () => Promise<void>;
  savePlatformProfile: (values: Record<string, unknown>, imageSelections: PlatformProfile["image_selections"]) => Promise<void>;
}) {
  return <div className="image-products-workspace">
    <div className="human-card image-product-directory-card">
      <div className="human-card-title">
        <h2>产品清单</h2>
        <span>{products.length} 个产品 · 产品档案字段由所选平台模板定义</span>
      </div>
      <div className="image-product-bulkbar">
        <div>
          <b>批量自定义字段</b>
          <span>已选 {selectedProductIds.length} 个产品。先选择模板及其自定义字段，填写的值将覆盖所选产品的该字段。</span>
        </div>
        <div className="image-bulk-fields"><select value={platformTemplateId} onChange={event => { setPlatformTemplateId(event.target.value); setBatchPlatformFieldKey(""); }}><option value="">选择平台模板</option>{platformTemplates.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><select value={batchPlatformFieldKey} disabled={!currentPlatformTemplate} onChange={event => setBatchPlatformFieldKey(event.target.value)}><option value="">选择自定义字段</option>{currentPlatformTemplate?.fields.map(field => <option key={field.key} value={field.key}>{field.label}</option>)}</select><input value={batchPlatformFieldValue} onChange={event => setBatchPlatformFieldValue(event.target.value)} placeholder="批量填写字段值" /><button type="button" className="human-secondary" disabled={busy || !selectedProductIds.length || !batchPlatformFieldKey} onClick={batchEditPlatformProfiles}>批量保存字段</button><button type="button" className="human-secondary" disabled={!selectedProductIds.length} onClick={() => setSelectedProductIds([])}>取消勾选</button><button type="button" className="human-danger" disabled={busy || !selectedProductIds.length} onClick={() => setConfirmation({ title: `删除所选 ${selectedProductIds.length} 个产品条目？`, message: "将删除产品档案、AI 任务和平台资料。默认保留原始照片并退回待分配区。", confirmLabel: "删除条目，保留原图", optionLabel: "删除条目和原图", onConfirm: deleteSourceAssets => deleteImageProducts(selectedProductIds, deleteSourceAssets) })}>删除所选条目</button></div>
      </div>
      <div className="image-table-wrap image-product-table-wrap"><table className="image-ops-table image-product-directory-table"><thead><tr><th>选择</th><th>唯一索引</th><th>产品名称</th><th>实拍图</th><th>状态</th><th>操作</th></tr></thead><tbody>
        {products.map(product => <tr key={product.id} className={selected?.id === product.id ? "active" : ""} onClick={() => setSelectedId(product.id)}>
          <td><input type="checkbox" checked={selectedProductIds.includes(product.id)} onChange={event => setSelectedProductIds(ids => event.target.checked ? [...new Set([...ids, product.id])] : ids.filter(id => id !== product.id))} onClick={event => event.stopPropagation()} /></td>
          <td><b>{product.product_code}</b></td>
          <td>{product.name || "未命名"}</td>
          <td>{product.reference_count} 张</td>
          <td><Pill value={product.status} /></td>
          <td><div className="image-product-row-actions"><button type="button" className="human-secondary compact" onClick={event => { event.stopPropagation(); editImageProduct(product.id); }}>编辑</button><button type="button" className="human-danger compact" onClick={event => { event.stopPropagation(); setConfirmation({ title: `删除产品“${product.name || product.product_code}”？`, message: "将删除该产品的档案、AI 任务和平台资料。默认保留原始照片并退回待分配区。", confirmLabel: "删除产品，保留原图", optionLabel: "删除产品和原图", onConfirm: deleteSourceAssets => deleteImageProducts([product.id], deleteSourceAssets) }); }}>删除</button></div></td>
        </tr>)}
        {products.length === 0 && <tr><td colSpan={6}>暂无产品资料。请先在“拍摄分组”确认产品组。</td></tr>}
      </tbody></table></div>
    </div>
    <PlatformTemplateManager platformTemplateId={platformTemplateId} platformTemplates={platformTemplates} platformTemplateName={platformTemplateName} platformTemplatePlatform={platformTemplatePlatform} platformTemplateEntryUrl={platformTemplateEntryUrl} platformFields={platformFields} platformImageSlots={platformImageSlots} busy={busy} setPlatformTemplateId={setPlatformTemplateId} setPlatformTemplateName={setPlatformTemplateName} setPlatformTemplatePlatform={setPlatformTemplatePlatform} setPlatformTemplateEntryUrl={setPlatformTemplateEntryUrl} setPlatformFields={setPlatformFields} setPlatformImageSlots={setPlatformImageSlots} setConfirmation={setConfirmation} newPlatformTemplate={newPlatformTemplate} deletePlatformTemplate={deletePlatformTemplate} savePlatformTemplate={savePlatformTemplate} />
    <div className="human-card image-product-editor-card" ref={imageProductEditorRef}>
      <div className="human-card-title"><h2>产品标识与模板档案</h2><span>{selected ? `${selected.product_code} · 实拍图完整度 ${completion}%` : "请选择产品"}</span></div>
      <section className="image-product-editor-section">
        <div className="image-product-editor-section-title">
          <b>产品标识</b>
          <span>产品序列号由系统生成，只允许修改产品名称。</span>
        </div>
        <form className="image-product-form" onSubmit={saveProduct}>
          <label>产品序列号<input value={form.product_code} readOnly placeholder="由创建产品组时自动生成" required /></label>
          <label>产品名称<input ref={imageProductNameRef} value={form.name} onChange={event => setForm(value => ({ ...value, name: event.target.value }))} placeholder="珍珠流苏金色发簪" required /></label>
          <div className="image-product-form-actions"><button disabled={busy || !selected}>{busy && <LoaderCircle className="spin" />}保存产品名称</button></div>
        </form>
      </section>
      <section className="image-product-editor-section">
        <div className="image-product-editor-section-title">
          <b>模板档案</b>
          <span>选择平台模板后，为当前产品创建并填写该平台需要的自定义字段。</span>
        </div>
        <div className="image-platform-profile-toolbar"><select value={platformTemplateId} onChange={event => setPlatformTemplateId(event.target.value)}><option value="">选择平台模板</option>{platformTemplates.map(item => <option key={item.id} value={item.id}>{item.name} · {item.platform || "未标注平台"}</option>)}</select><button type="button" disabled={!selected || !platformTemplateId || busy || Boolean(currentPlatformProfile)} onClick={ensurePlatformProfile}>创建模板档案</button></div>
        {!currentPlatformTemplate && <div className="human-note">先在上方新建平台模板并添加自定义字段；产品资料不会预设颜色、尺码、库存等字段。</div>}
        {currentPlatformProfile && currentPlatformTemplate && <><div className="image-platform-fields">{currentPlatformTemplate.fields.map(field => <label key={field.key}>{field.label}{field.required ? " *" : ""}{field.type === "select" ? <select value={String(platformProfileValues[field.key] ?? "")} onChange={event => setPlatformProfileValues(values => ({ ...values, [field.key]: event.target.value }))}><option value="">请选择</option>{field.options.map(option => <option key={option} value={option}>{option}</option>)}</select> : field.type === "textarea" || field.type === "rich_text" || field.type === "sku_matrix" ? <textarea value={String(platformProfileValues[field.key] ?? "")} onChange={event => setPlatformProfileValues(values => ({ ...values, [field.key]: event.target.value }))} placeholder="人工填写" /> : <input type={field.type === "number" ? "number" : "text"} value={String(platformProfileValues[field.key] ?? "")} onChange={event => setPlatformProfileValues(values => ({ ...values, [field.key]: event.target.value }))} />}</label>)}</div><div className="image-platform-actions"><button type="button" onClick={() => savePlatformProfile(platformProfileValues, platformImageSelections)} disabled={busy}>保存模板档案字段</button><Pill value={currentPlatformProfile.status} /></div></>}
      </section>
    </div>
    <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
  </div>;
}
