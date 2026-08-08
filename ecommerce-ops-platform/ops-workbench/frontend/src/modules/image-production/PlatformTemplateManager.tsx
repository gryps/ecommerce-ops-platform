import type { Dispatch, SetStateAction } from "react";
import type { DeleteConfirmation, PlatformField, PlatformImageSlot, PlatformTemplate } from "../../types";

export function PlatformTemplateManager({
  platformTemplateId,
  platformTemplates,
  platformTemplateName,
  platformTemplatePlatform,
  platformTemplateEntryUrl,
  platformFields,
  platformImageSlots,
  busy,
  setPlatformTemplateId,
  setPlatformTemplateName,
  setPlatformTemplatePlatform,
  setPlatformTemplateEntryUrl,
  setPlatformFields,
  setPlatformImageSlots,
  setConfirmation,
  newPlatformTemplate,
  deletePlatformTemplate,
  savePlatformTemplate,
}: {
  platformTemplateId: string;
  platformTemplates: PlatformTemplate[];
  platformTemplateName: string;
  platformTemplatePlatform: string;
  platformTemplateEntryUrl: string;
  platformFields: PlatformField[];
  platformImageSlots: PlatformImageSlot[];
  busy: boolean;
  setPlatformTemplateId: Dispatch<SetStateAction<string>>;
  setPlatformTemplateName: Dispatch<SetStateAction<string>>;
  setPlatformTemplatePlatform: Dispatch<SetStateAction<string>>;
  setPlatformTemplateEntryUrl: Dispatch<SetStateAction<string>>;
  setPlatformFields: Dispatch<SetStateAction<PlatformField[]>>;
  setPlatformImageSlots: Dispatch<SetStateAction<PlatformImageSlot[]>>;
  setConfirmation: Dispatch<SetStateAction<DeleteConfirmation | null>>;
  newPlatformTemplate: () => void;
  deletePlatformTemplate: () => Promise<void>;
  savePlatformTemplate: () => Promise<void>;
}) {
  return <div className="human-card image-platform-template-card"><div className="human-card-title"><h2>产品档案模板</h2><span>抖音、快手、视频号各维护一套；字段和图片槽位都在这里定义</span></div>
    <div className="image-platform-template-select"><select value={platformTemplateId} onChange={event => setPlatformTemplateId(event.target.value)}><option value="">新建平台模板</option>{platformTemplates.map(item => <option key={item.id} value={item.id}>{item.name} · {item.platform || "未标注平台"}</option>)}</select><button type="button" className="human-secondary" onClick={newPlatformTemplate}>新建</button>{platformTemplateId && <button type="button" className="human-danger" onClick={() => setConfirmation({ title: `删除平台模板“${platformTemplateName}”？`, message: "该模板的字段、图片槽位和所有关联的平台产品档案都会删除。", onConfirm: deletePlatformTemplate })}>删除模板</button>}</div>
    <div className="image-platform-meta"><label>模板名称<input value={platformTemplateName} onChange={event => setPlatformTemplateName(event.target.value)} placeholder="抖音商品模板" /></label><label>平台名称<input value={platformTemplatePlatform} onChange={event => setPlatformTemplatePlatform(event.target.value)} placeholder="抖音" /></label><label className="wide">商品发布页入口<input value={platformTemplateEntryUrl} onChange={event => setPlatformTemplateEntryUrl(event.target.value)} placeholder="https://..." /></label></div>
    <div className="image-table-wrap"><table className="image-ops-table"><thead><tr><th>字段键</th><th>显示名称</th><th>填写类型</th><th>必填</th><th>默认值 / 下拉选项</th><th>网页选择器</th><th></th></tr></thead><tbody>{platformFields.map((field, index) => <tr key={`${field.key}-${index}`}><td><input value={field.key} onChange={event => setPlatformFields(rows => rows.map((row, i) => i === index ? { ...row, key: event.target.value } : row))} /></td><td><input value={field.label} onChange={event => setPlatformFields(rows => rows.map((row, i) => i === index ? { ...row, label: event.target.value } : row))} /></td><td><select value={field.type} onChange={event => setPlatformFields(rows => rows.map((row, i) => i === index ? { ...row, type: event.target.value as PlatformField["type"] } : row))}>{["text", "number", "select", "textarea", "rich_text", "sku_matrix"].map(kind => <option key={kind} value={kind}>{kind}</option>)}</select></td><td><input type="checkbox" checked={field.required} onChange={event => setPlatformFields(rows => rows.map((row, i) => i === index ? { ...row, required: event.target.checked } : row))} /></td><td><input value={Array.isArray(field.options) && field.options.length ? field.options.join("、") : String(field.default ?? "")} onChange={event => setPlatformFields(rows => rows.map((row, i) => i === index ? { ...row, options: field.type === "select" ? event.target.value.split(/[、,，]/).filter(Boolean) : [], default: field.type === "select" ? "" : event.target.value } : row))} placeholder={field.type === "select" ? "选项用顿号分隔" : "默认值"} /></td><td><input value={field.selector} onChange={event => setPlatformFields(rows => rows.map((row, i) => i === index ? { ...row, selector: event.target.value } : row))} placeholder="CSS / 页面定位" /></td><td><button type="button" className="human-danger compact" onClick={() => setPlatformFields(rows => rows.filter((_, i) => i !== index))}>移除</button></td></tr>)}{!platformFields.length && <tr><td colSpan={7}>尚未添加字段。可先保存空模板，后续按平台填写要求增加字段。</td></tr>}</tbody></table></div>
    <div className="image-platform-actions"><button type="button" className="human-secondary" onClick={() => setPlatformFields(rows => [...rows, { key: `field_${rows.length + 1}`, label: "新字段", type: "text", required: false, default: "", options: [], selector: "" }])}>添加字段</button><button type="button" onClick={savePlatformTemplate} disabled={busy}>保存平台模板</button></div>
    <div className="image-table-wrap"><table className="image-ops-table"><thead><tr><th>图片槽位键</th><th>显示名称</th><th>必填</th><th>最多图片</th><th>网页选择器</th><th></th></tr></thead><tbody>{platformImageSlots.map((slot, index) => <tr key={`${slot.key}-${index}`}><td><input value={slot.key} onChange={event => setPlatformImageSlots(rows => rows.map((row, i) => i === index ? { ...row, key: event.target.value } : row))} /></td><td><input value={slot.label} onChange={event => setPlatformImageSlots(rows => rows.map((row, i) => i === index ? { ...row, label: event.target.value } : row))} /></td><td><input type="checkbox" checked={slot.required} onChange={event => setPlatformImageSlots(rows => rows.map((row, i) => i === index ? { ...row, required: event.target.checked } : row))} /></td><td><input type="number" min="1" max="50" value={slot.max_count} onChange={event => setPlatformImageSlots(rows => rows.map((row, i) => i === index ? { ...row, max_count: Number(event.target.value) || 1 } : row))} /></td><td><input value={slot.selector} onChange={event => setPlatformImageSlots(rows => rows.map((row, i) => i === index ? { ...row, selector: event.target.value } : row))} /></td><td><button type="button" className="human-danger compact" onClick={() => setPlatformImageSlots(rows => rows.filter((_, i) => i !== index))}>移除</button></td></tr>)}{!platformImageSlots.length && <tr><td colSpan={6}>尚未添加图片槽位。</td></tr>}</tbody></table></div>
    <button type="button" className="human-secondary" onClick={() => setPlatformImageSlots(rows => [...rows, { key: `image_${rows.length + 1}`, label: "商品主图", required: false, max_count: 1, selector: "" }])}>添加图片槽位</button>
  </div>;
}
