import { useEffect, useRef, useState } from "react";
import { FolderOpen, LoaderCircle, Sparkles, Volume2 } from "lucide-react";
import { api, apiBlob } from "../../api";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import { Pill } from "../../components/Pill";
import type { CopyItem, DeleteConfirmation, DraftDirectory, JianyingDraft, MusicResource, Narration } from "../../types";
import { fuzzyRows } from "../../utils/fuzzy";

export function DraftProduction({ copies, narrations, music, drafts, act }: {
  copies: CopyItem[]; narrations: Narration[]; music: MusicResource[]; drafts: JianyingDraft[];
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
}) {
  const [copyId, setCopyId] = useState(""); const [narrationId, setNarrationId] = useState(""); const [musicId, setMusicId] = useState("");
  const [draftBusy, setDraftBusy] = useState(false); const [draftError, setDraftError] = useState("");
  const [directory, setDirectory] = useState<DraftDirectory | null>(null);
  const [manualDir, setManualDir] = useState("");
  const [dirBusy, setDirBusy] = useState(false);
  const [dirError, setDirError] = useState("");
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const [copyPage, setCopyPage] = useState(0); const [narrationPage, setNarrationPage] = useState(0); const [musicPage, setMusicPage] = useState(0); const [draftPage, setDraftPage] = useState(0);
  const [copyQuery, setCopyQuery] = useState(""); const [narrationQuery, setNarrationQuery] = useState(""); const [musicQuery, setMusicQuery] = useState("");
  const [previewId, setPreviewId] = useState(""); const [previewBusyId, setPreviewBusyId] = useState(""); const [previewError, setPreviewError] = useState("");
  const [duplicatePrompt, setDuplicatePrompt] = useState<{ count: number } | null>(null);
  const draftPlayerRef = useRef<HTMLAudioElement | null>(null); const draftAudioUrlRef = useRef(""); const draftPlayRequestRef = useRef(0);
  const approvedNarrations = narrations.filter(item => item.status === "approved");
  const readyMusic = music.filter(item => item.status === "ready");
  const filteredCopies = fuzzyRows(copies, copyQuery, item => `${item.content} ${item.product_name || ""} ${item.source}`, copies.length);
  const filteredNarrations = fuzzyRows(approvedNarrations, narrationQuery, item => `${item.approved_text} ${item.voice_source} ${item.subtitle_cues.length}`, approvedNarrations.length);
  const filteredMusic = fuzzyRows(readyMusic, musicQuery, item => `${item.name} ${item.custom_tags.join(" ")} ${item.duration_seconds}`, readyMusic.length);
  const selectedCopy = copies.find(item => item.id === copyId);
  const selectedNarration = approvedNarrations.find(item => item.id === narrationId);
  const selectedMusic = readyMusic.find(item => item.id === musicId);
  const selectedCount = [copyId, narrationId, musicId].filter(Boolean).length;
  const pageSize = 20;
  const pageRows = <T,>(rows: T[], page: number) => rows.slice(page * pageSize, page * pageSize + pageSize);
  useEffect(() => {
    if (draftPage > 0 && draftPage * pageSize >= drafts.length) setDraftPage(Math.max(0, Math.ceil(drafts.length / pageSize) - 1));
  }, [draftPage, drafts.length]);
  const draftDuplicatePayload = () => ({ copy_content_id: copyId || null, narration_asset_id: narrationId || null, music_resource_id: musicId || null });
  function stopPreview(updateState = true) {
    draftPlayRequestRef.current += 1;
    if (draftPlayerRef.current) { draftPlayerRef.current.pause(); draftPlayerRef.current.currentTime = 0; draftPlayerRef.current = null; }
    if (draftAudioUrlRef.current) { URL.revokeObjectURL(draftAudioUrlRef.current); draftAudioUrlRef.current = ""; }
    if (updateState) { setPreviewId(""); setPreviewBusyId(""); }
  }
  useEffect(() => () => stopPreview(false), []);
  async function listenPreview(kind: "narration" | "music", item: Narration | MusicResource) {
    const targetId = `${kind}:${item.id}`;
    if (previewId === targetId && !previewBusyId) { stopPreview(); return; }
    stopPreview();
    const requestId = draftPlayRequestRef.current;
    setPreviewId(targetId); setPreviewBusyId(targetId); setPreviewError("");
    try {
      const blob = await apiBlob(kind === "narration" ? `/human/narrations/${item.id}/audio` : `/music-resources/${item.id}/audio`);
      if (requestId !== draftPlayRequestRef.current) return;
      const url = URL.createObjectURL(blob); const player = new Audio(url);
      draftAudioUrlRef.current = url; draftPlayerRef.current = player; setPreviewBusyId("");
      player.onended = () => { if (draftPlayerRef.current === player) stopPreview(); };
      await player.play();
    } catch (reason) {
      if (requestId === draftPlayRequestRef.current) {
        stopPreview();
        setPreviewError(reason instanceof Error ? reason.message : "试听失败");
      }
    }
  }
  async function loadDirectory() {
    setDirBusy(true); setDirError("");
    try {
      const value = await api<DraftDirectory>("/human/jianying-drafts/directory");
      setDirectory(value); setManualDir(value.path || "");
    } catch (reason) {
      setDirError(reason instanceof Error ? reason.message : "剪映草稿目录检测失败");
    } finally { setDirBusy(false); }
  }
  useEffect(() => { loadDirectory(); }, []);
  async function confirmDirectory() {
    if (dirBusy || !manualDir.trim()) return;
    setDirBusy(true); setDirError("");
    try {
      const value = await api<DraftDirectory>("/human/jianying-drafts/directory", { method: "PUT", body: JSON.stringify({ path: manualDir.trim() }) });
      setDirectory(value); setManualDir(value.path || "");
    } catch (reason) {
      setDirError(reason instanceof Error ? reason.message : "剪映草稿目录确认失败");
    } finally { setDirBusy(false); }
  }
  async function generateDraft() {
    if (draftBusy || !directory?.exists || !directory.path || selectedCount === 0) return;
    setDraftError("");
    const duplicate = await api<{ count: number }>("/human/jianying-drafts/duplicate-count", { method: "POST", body: JSON.stringify(draftDuplicatePayload()) });
    if (duplicate.count > 0) {
      setDuplicatePrompt({ count: duplicate.count });
      return;
    }
    await submitDraft();
  }
  async function resetDuplicateCounter() {
    if (draftBusy || selectedCount === 0) return;
    const success = await act(() => api("/human/jianying-drafts/duplicate-counter/reset", { method: "POST", body: JSON.stringify(draftDuplicatePayload()) }), "重复计数器已复位");
    if (success) setDuplicatePrompt(null);
  }
  async function submitDraft() {
    if (draftBusy || !directory?.exists || !directory.path || selectedCount === 0) return;
    setDuplicatePrompt(null);
    setDraftBusy(true); setDraftError("");
    try {
      const success = await act(() => api("/human/jianying-drafts", { method: "POST", body: JSON.stringify({ name: "", destination_dir: directory.path, copy_content_id: copyId || null, narration_asset_id: narrationId || null, music_resource_id: musicId || null }) }), "剪映草稿已生成到剪映草稿目录");
      if (!success) setDraftError("剪映草稿生成失败，请查看页面上方的错误提示。");
    } finally { setDraftBusy(false); }
  }
  function pager(total: number, page: number, setPage: (value: number) => void) {
    const pages = Math.max(1, Math.ceil(total / pageSize));
    return <div className="draft-library-pager"><button type="button" className="human-secondary" disabled={page <= 0} onClick={() => setPage(page - 1)}>上一页</button><span>{page + 1} / {pages}</span><button type="button" className="human-secondary" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>下一页</button></div>;
  }
  return <section className="human-page draft-production-page">
    <div className="human-card full draft-directory-card"><div className="human-card-title"><h2>剪映草稿目录</h2><span>{directory?.exists ? "已确认" : "待确认"}</span></div><div className="human-form draft-directory-form">
        <label className="draft-directory-input">当前目录<input value={manualDir} disabled={dirBusy || draftBusy} onChange={event => setManualDir(event.target.value)} placeholder="未检测到时可手动填写完整目录" /></label>
        <button type="button" className="human-secondary draft-directory-detect" disabled={dirBusy || draftBusy} onClick={loadDirectory}><FolderOpen />{dirBusy ? "正在检测…" : "重新检测"}</button>
        <button type="button" className="draft-directory-confirm" disabled={dirBusy || draftBusy || !manualDir.trim()} onClick={confirmDirectory}>{dirBusy && <LoaderCircle className="spin" />}{dirBusy ? "正在确认…" : "确认目录"}</button>
        <small className="draft-directory-path" title={directory?.exists ? (directory.windows_path || directory.path) : ""}>{directory?.exists ? (directory.windows_path || directory.path) : "未确认有效目录"}</small>
        {dirError && <div className="copy-generation-progress error" role="alert"><div><b>目录不可用</b><span>{dirError}</span></div></div>}
      </div></div>
    <div className="human-card full draft-selection-card"><div className="human-card-title"><h2>物料清单</h2><span>{selectedCount} 项已选</span></div><div className="draft-selection-row">
        <article><b title="文案内容">文案内容</b><span title={selectedCopy?.content || "未选择"}>{selectedCopy?.content || "未选择"}</span>{selectedCopy && <button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setCopyId("")}>取消</button>}</article>
        <article><b title="旁白与字幕">旁白与字幕</b><span title={selectedNarration?.approved_text || "未选择"}>{selectedNarration?.approved_text || "未选择"}</span>{selectedNarration && <button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setNarrationId("")}>取消</button>}</article>
        <article><b title="背景音乐">背景音乐</b><span title={selectedMusic ? `${selectedMusic.name} · ${selectedMusic.duration_seconds.toFixed(1)} 秒` : "未选择"}>{selectedMusic ? `${selectedMusic.name} · ${selectedMusic.duration_seconds.toFixed(1)} 秒` : "未选择"}</span>{selectedMusic && <button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setMusicId("")}>取消</button>}</article>
        <div className="draft-generate-box"><button disabled={draftBusy || !directory?.exists || !directory.path || selectedCount === 0} onClick={generateDraft}>{draftBusy ? <LoaderCircle className="spin" /> : <Sparkles />}{draftBusy ? "正在生成…" : "生成草稿"}</button><span>{directory?.exists ? "目录可用" : "目录未确认"}</span></div>
        {draftBusy && <div className="copy-generation-progress draft-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>剪映草稿正在生成</b><span>系统正在校验资源并写入剪映草稿目录，完成前请勿重复提交。</span></div></div>}
        {draftError && !draftBusy && <div className="copy-generation-progress error draft-progress" role="alert"><div><b>生成失败</b><span>{draftError}</span></div></div>}
      </div></div>
    <div className="draft-library-columns full">
      <div className="human-card draft-library-card"><div className="human-card-title"><h2>文案内容库</h2><span>{filteredCopies.length}/{copies.length} 条</span></div><input className="draft-library-search" value={copyQuery} onChange={event => { setCopyQuery(event.target.value); setCopyPage(0); }} placeholder="模糊查询文案、产品或来源" /><div className="draft-library-list">{pageRows(filteredCopies, copyPage).map(item => { const meta = `${item.product_name || "全局通用"} · ${item.source === "model" ? "模型生成" : item.source === "original" ? "参考原文" : "人工录入"}`; return <article key={item.id} className={copyId === item.id ? "selected" : ""}><button type="button" className="draft-library-select" disabled={draftBusy} onClick={() => setCopyId(item.id)}><b title={item.content}>{item.content}</b><span title={meta}>{meta}</span></button></article>; })}</div>{pager(filteredCopies.length, copyPage, setCopyPage)}</div>
      <div className="human-card draft-library-card"><div className="human-card-title"><h2>旁白与字幕库</h2><span>{filteredNarrations.length}/{approvedNarrations.length} 条</span></div><input className="draft-library-search" value={narrationQuery} onChange={event => { setNarrationQuery(event.target.value); setNarrationPage(0); }} placeholder="模糊查询旁白、字幕数量或来源" />{previewError && previewId.startsWith("narration:") && <div className="copy-generation-progress error draft-preview-error" role="alert"><div><b>旁白试听失败</b><span>{previewError}</span></div></div>}<div className="draft-library-list">{pageRows(filteredNarrations, narrationPage).map(item => { const meta = `${item.subtitle_cues.length} 条字幕 · ${item.voice_source === "model" ? "模型配音" : "人工资源"}`; return <article key={item.id} className={narrationId === item.id ? "selected" : ""}><button type="button" className="draft-library-select" disabled={draftBusy} onClick={() => setNarrationId(item.id)}><b title={item.approved_text}>{item.approved_text}</b><span title={meta}>{meta}</span></button><div className="draft-library-actions"><button type="button" className="human-secondary" disabled={Boolean(previewBusyId && previewBusyId !== `narration:${item.id}`)} onClick={() => listenPreview("narration", item)}>{previewBusyId === `narration:${item.id}` ? <LoaderCircle className="spin" /> : <Volume2 />}{previewId === `narration:${item.id}` && !previewBusyId ? "停止" : previewBusyId === `narration:${item.id}` ? "加载" : "试听"}</button></div></article>; })}</div>{pager(filteredNarrations.length, narrationPage, setNarrationPage)}</div>
      <div className="human-card draft-library-card"><div className="human-card-title"><h2>背景音乐库</h2><span>{filteredMusic.length}/{readyMusic.length} 条</span></div><input className="draft-library-search" value={musicQuery} onChange={event => { setMusicQuery(event.target.value); setMusicPage(0); }} placeholder="模糊查询名称、标签或时长" />{previewError && previewId.startsWith("music:") && <div className="copy-generation-progress error draft-preview-error" role="alert"><div><b>音乐试听失败</b><span>{previewError}</span></div></div>}<div className="draft-library-list">{pageRows(filteredMusic, musicPage).map(item => { const meta = `${item.duration_seconds.toFixed(1)} 秒 · ${item.custom_tags.length ? item.custom_tags.join(" / ") : "无标签"}`; return <article key={item.id} className={musicId === item.id ? "selected" : ""}><button type="button" className="draft-library-select" disabled={draftBusy} onClick={() => setMusicId(item.id)}><b title={item.name}>{item.name}</b><span title={meta}>{meta}</span></button><div className="draft-library-actions"><button type="button" className="human-secondary" disabled={Boolean(previewBusyId && previewBusyId !== `music:${item.id}`)} onClick={() => listenPreview("music", item)}>{previewBusyId === `music:${item.id}` ? <LoaderCircle className="spin" /> : <Volume2 />}{previewId === `music:${item.id}` && !previewBusyId ? "停止" : previewBusyId === `music:${item.id}` ? "加载" : "试听"}</button></div></article>; })}</div>{pager(filteredMusic.length, musicPage, setMusicPage)}</div>
    </div>
    <div className="human-card full"><div className="human-card-title"><h2>剪映草稿记录</h2><span>最新在前，每页 20 条，共 {drafts.length} 条</span></div><div className="simple-resource-list">{pageRows(drafts, draftPage).map(item => <article key={item.id}><div><b title={item.name}>{item.name}</b><span title={item.draft_path}>{item.draft_path || "未记录目录"} · {new Date(item.created_at).toLocaleString()}</span></div><div><Pill value={item.status} /><button className="human-secondary danger" onClick={() => setConfirmation({ title: `删除草稿记录“${item.name}”？`, message: "只删除工作台中的草稿记录，不删除磁盘上的剪映草稿文件夹。", onConfirm: () => act(() => api(`/human/jianying-drafts/${item.id}`, { method: "DELETE" }), "剪映草稿记录已删除") })}>删除</button></div></article>)}</div>{pager(drafts.length, draftPage, setDraftPage)}<ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />{duplicatePrompt && <div className="confirm-dialog-backdrop" role="presentation"><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="draft-duplicate-title"><div><b id="draft-duplicate-title">重复物料组合</b><span>当前选择的文案、旁白与字幕、背景音乐组合此前已生成 {duplicatePrompt.count} 次。系统不会阻止再次生成。</span></div><div><button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setDuplicatePrompt(null)}>取消</button><button type="button" className="human-secondary" disabled={draftBusy} onClick={resetDuplicateCounter}>计数器复位</button><button type="button" disabled={draftBusy} onClick={submitDraft}>{draftBusy && <LoaderCircle className="spin" />}{draftBusy ? "正在生成…" : "继续生成"}</button></div></section></div>}</div>
  </section>;
}
