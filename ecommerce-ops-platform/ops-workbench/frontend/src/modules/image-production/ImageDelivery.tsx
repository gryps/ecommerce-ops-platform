import type { Dispatch, SetStateAction } from "react";
import { Upload } from "lucide-react";
import { BrowserAutomationMask } from "../../components/BrowserAutomationMask";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import { Pill } from "../../components/Pill";
import type { BrowserSession, DeleteConfirmation, ImageProduct, ImageTask, PlatformProfile, PlatformTemplate } from "../../types";

export function ImageDelivery({
  products,
  selected,
  selectedId,
  platformTemplateId,
  platformTemplates,
  currentPlatformTemplate,
  currentPlatformProfile,
  tasks,
  platformImageSelections,
  platformProfileValues,
  platformUrl,
  browserSession,
  confirmation,
  busy,
  setSelectedId,
  setPlatformTemplateId,
  setPlatformImageSelections,
  setPlatformUrl,
  setConfirmation,
  ensurePlatformProfile,
  savePlatformProfile,
  startBrowserAutomation,
  stopBrowserAutomation,
}: {
  products: ImageProduct[];
  selected: ImageProduct | null;
  selectedId: string;
  platformTemplateId: string;
  platformTemplates: PlatformTemplate[];
  currentPlatformTemplate: PlatformTemplate | null;
  currentPlatformProfile: PlatformProfile | null;
  tasks: ImageTask[];
  platformImageSelections: PlatformProfile["image_selections"];
  platformProfileValues: Record<string, unknown>;
  platformUrl: string;
  browserSession: BrowserSession | null;
  confirmation: DeleteConfirmation | null;
  busy: boolean;
  setSelectedId: Dispatch<SetStateAction<string>>;
  setPlatformTemplateId: Dispatch<SetStateAction<string>>;
  setPlatformImageSelections: Dispatch<SetStateAction<PlatformProfile["image_selections"]>>;
  setPlatformUrl: Dispatch<SetStateAction<string>>;
  setConfirmation: Dispatch<SetStateAction<DeleteConfirmation | null>>;
  ensurePlatformProfile: () => Promise<void>;
  savePlatformProfile: (values: Record<string, unknown>, imageSelections: PlatformProfile["image_selections"]) => Promise<void>;
  startBrowserAutomation: () => Promise<void>;
  stopBrowserAutomation: () => Promise<void>;
}) {
  return <>
    <div className="image-platform-layout delivery-only">
      <div className="human-card image-platform-profile-card"><div className="human-card-title"><h2>平台选图</h2><span>{selected ? `${selected.product_code} · ${selected.name}` : "请选择产品"}</span></div>
        <div className="image-platform-profile-toolbar"><select value={selectedId} onChange={event => setSelectedId(event.target.value)}><option value="">选择产品</option>{products.map(item => <option key={item.id} value={item.id}>{item.product_code} · {item.name}</option>)}</select><select value={platformTemplateId} onChange={event => setPlatformTemplateId(event.target.value)}><option value="">选择平台模板</option>{platformTemplates.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button type="button" disabled={!selected || !platformTemplateId || busy || Boolean(currentPlatformProfile)} onClick={ensurePlatformProfile}>创建平台档案</button></div>
        {!currentPlatformTemplate && <div className="human-note">平台模板和字段在“产品资料”中维护；这里仅选择已保存模板并配置平台图片槽位。</div>}
        {currentPlatformProfile && currentPlatformTemplate && <>
          <div className="image-platform-slots"><h3>人工选择审核通过的 AI 图</h3>{currentPlatformTemplate.image_slots.map(slot => <article key={slot.key}><b>{slot.label}{slot.required ? " *" : ""}</b><span>最多 {slot.max_count} 张</span>{tasks.filter(task => task.product_id === selected?.id && task.review_status === "approved").flatMap(task => task.output_images.map((image, outputIndex) => ({ task, image, outputIndex }))).map(({ task, image, outputIndex }) => { const checked = (platformImageSelections[slot.key] ?? []).some(item => item.task_id === task.id && item.output_index === outputIndex); return <label key={`${task.id}-${outputIndex}`}><input type="checkbox" checked={checked} onChange={event => setPlatformImageSelections(rows => { const current = rows[slot.key] ?? []; const next = event.target.checked ? [...current, { task_id: task.id, output_index: outputIndex, name: image.name, url: image.url }] : current.filter(item => item.task_id !== task.id || item.output_index !== outputIndex); return { ...rows, [slot.key]: next.slice(0, slot.max_count) }; })} /><span>{image.image_type} · {image.name}</span></label>; })}{!tasks.some(task => task.product_id === selected?.id && task.review_status === "approved" && task.output_images.length) && <p>暂无审核通过的 AI 图。</p>}</article>)}{!currentPlatformTemplate.image_slots.length && <p>该模板还没有图片槽位，请先到“产品资料”添加。</p>}</div>
          <div className="image-platform-actions"><button type="button" onClick={() => savePlatformProfile(platformProfileValues, platformImageSelections)} disabled={busy}>保存平台选图</button><Pill value={currentPlatformProfile.status} /></div>
        </>}
      </div>
      <div className="human-card image-platform-browser-card"><div className="human-card-title"><h2>保存平台草稿</h2><span>仅在字段和选图完整后进入浏览器</span></div><div className="image-policy-list"><p>打开独立指定浏览器后，请自行登录；验证码、风控和最终发布始终由你处理。</p><p>模板需配置页面选择器后，才能逐字段填写、上传图片并保存草稿；当前只启动登录会话，不会自动发布或绕过安全校验。</p></div><div className="platform-browser-launch"><label>商品发布页地址<input value={platformUrl || currentPlatformTemplate?.entry_url || ""} onChange={event => setPlatformUrl(event.target.value)} placeholder="https://平台后台/商品发布" /></label><button type="button" disabled={Boolean(browserSession) || currentPlatformProfile?.status !== "waiting_auto_fill"} onClick={startBrowserAutomation}><Upload />登录并继续自动填报</button></div></div>
    </div>
    {browserSession && <BrowserAutomationMask session={browserSession} onExit={stopBrowserAutomation} />}
    <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
  </>;
}
