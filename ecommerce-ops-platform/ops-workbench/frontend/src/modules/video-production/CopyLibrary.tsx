import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { LoaderCircle, Sparkles, Upload, Volume2 } from "lucide-react";
import { api, apiBlob } from "../../api";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import { Pill } from "../../components/Pill";
import { usePersistentOperation } from "../../hooks/usePersistentOperation";
import type { CopyAnalysis, CopyCandidate, CopyItem, DeleteConfirmation, Narration, VoiceCatalogItem } from "../../types";

export function CopyLibrary({ copies, narrations, act, reload }: {
  copies: CopyItem[]; narrations: Narration[];
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
  reload: () => Promise<void>;
}) {
  const [tab, setTab] = useState<"copies" | "voices" | "narrations">("copies");
  const [reference, setReference] = useState("");
  const [activeRecord, setActiveRecord] = useState<CopyAnalysis | null>(null);
  const [history, setHistory] = useState<CopyAnalysis[]>([]); const [historyTotal, setHistoryTotal] = useState(0); const [historyPage, setHistoryPage] = useState(1);
  const [generationError, setGenerationError] = useState(""); const [generationNotice, setGenerationNotice] = useState("");
  const [narrationText, setNarrationText] = useState(""); const [selectedCopyId, setSelectedCopyId] = useState("");
  const [copySearch, setCopySearch] = useState(""); const [copySearchOpen, setCopySearchOpen] = useState(false); const [copySearchBusy, setCopySearchBusy] = useState(false); const [copySuggestions, setCopySuggestions] = useState<CopyItem[]>([]); const [selectedNarrationCopy, setSelectedNarrationCopy] = useState<CopyItem | null>(null);
  const [narrationBusy, setNarrationBusy] = useState(false); const [narrationError, setNarrationError] = useState("");
  const [transcriptionLink, setTranscriptionLink] = useState(""); const [transcriptionFile, setTranscriptionFile] = useState<File | null>(null); const [transcriptionText, setTranscriptionText] = useState(""); const [transcriptionBusy, setTranscriptionBusy] = useState(false); const [transcriptionError, setTranscriptionError] = useState("");
  const [previewingVoice, setPreviewingVoice] = useState(""); const [previewLoading, setPreviewLoading] = useState(false); const [voicePreviewError, setVoicePreviewError] = useState("");
  const [voiceSequenceInput, setVoiceSequenceInput] = useState(""); const [selectedCatalogVoice, setSelectedCatalogVoice] = useState<VoiceCatalogItem | null>(null); const [voiceSequenceError, setVoiceSequenceError] = useState("");
  const [voiceCatalog, setVoiceCatalog] = useState<VoiceCatalogItem[]>([]); const [voiceCatalogTotal, setVoiceCatalogTotal] = useState(0); const [voiceCatalogPage, setVoiceCatalogPage] = useState(1); const [voiceCatalogQuery, setVoiceCatalogQuery] = useState(""); const [voiceCatalogGender, setVoiceCatalogGender] = useState(""); const [voiceCatalogAge, setVoiceCatalogAge] = useState(""); const [voiceCatalogScenario, setVoiceCatalogScenario] = useState("");
  const [voiceCatalogGenders, setVoiceCatalogGenders] = useState<string[]>([]); const [voiceCatalogAges, setVoiceCatalogAges] = useState<string[]>([]); const [voiceCatalogScenarios, setVoiceCatalogScenarios] = useState<string[]>([]);
  const voicePlayerRef = useRef<HTMLAudioElement | null>(null); const voiceAudioUrlRef = useRef(""); const voicePreviewRequestRef = useRef(0);
  const [playingNarrationId, setPlayingNarrationId] = useState(""); const narrationPlayerRef = useRef<HTMLAudioElement | null>(null); const narrationAudioUrlRef = useRef("");
  const [editingCopyId, setEditingCopyId] = useState<string | null>(null); const [editingCopy, setEditingCopy] = useState("");
  const [hiddenCopyIds, setHiddenCopyIds] = useState<string[]>([]);
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const visibleCopies = copies.filter(item => !hiddenCopyIds.includes(item.id));
  useEffect(() => { setHiddenCopyIds(ids => ids.filter(id => copies.some(item => item.id === id))); }, [copies]);
  useEffect(() => {
    if (!copySearchOpen || narrationBusy) return undefined;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setCopySearchBusy(true);
      try {
        const params = new URLSearchParams({ search: copySearch.trim(), limit: "10" });
        const result = await api<{ items: CopyItem[] }>(`/human/copies/library?${params}`);
        if (!cancelled) setCopySuggestions(result.items);
      } catch { if (!cancelled) setCopySuggestions([]); }
      finally { if (!cancelled) setCopySearchBusy(false); }
    }, 220);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [copySearch, copySearchOpen, narrationBusy]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ page: String(voiceCatalogPage), page_size: "20" });
      if (voiceCatalogQuery.trim()) params.set("q", voiceCatalogQuery.trim());
      if (voiceCatalogGender) params.set("gender", voiceCatalogGender);
      if (voiceCatalogAge) params.set("age", voiceCatalogAge);
      if (voiceCatalogScenario) params.set("scenario", voiceCatalogScenario);
      api<{ total: number; items: VoiceCatalogItem[]; genders?: string[]; ages?: string[]; scenarios?: string[] }>(`/human/voice-catalog?${params}`).then(value => { setVoiceCatalog(value.items); setVoiceCatalogTotal(value.total); setVoiceCatalogGenders(value.genders ?? ["女", "男"]); setVoiceCatalogAges(value.ages ?? []); setVoiceCatalogScenarios(value.scenarios ?? []); }).catch(() => { setVoiceCatalog([]); setVoiceCatalogTotal(0); });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [voiceCatalogPage, voiceCatalogQuery, voiceCatalogGender, voiceCatalogAge, voiceCatalogScenario]);
  useEffect(() => {
    setSelectedCatalogVoice(null); setVoiceSequenceError("");
    const raw = voiceSequenceInput.trim();
    if (!raw) return undefined;
    if (!/^\d+$/.test(raw)) { setVoiceSequenceError("请输入 1 至 597 的整数序号"); return undefined; }
    const timer = window.setTimeout(() => {
      api<VoiceCatalogItem>(`/human/voice-catalog/${Number(raw)}`).then(item => { setSelectedCatalogVoice(item); setVoiceSequenceError(""); setVoicePreviewError(""); stopVoicePreview(); }).catch(reason => { setSelectedCatalogVoice(null); setVoiceSequenceError(reason instanceof Error ? reason.message : "音色序号不存在"); });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [voiceSequenceInput]);
  function stopVoicePreview(updateState = true) {
    voicePreviewRequestRef.current += 1;
    if (voicePlayerRef.current) { voicePlayerRef.current.pause(); voicePlayerRef.current.currentTime = 0; voicePlayerRef.current = null; }
    if (voiceAudioUrlRef.current) { URL.revokeObjectURL(voiceAudioUrlRef.current); voiceAudioUrlRef.current = ""; }
    if (updateState) { setPreviewingVoice(""); setPreviewLoading(false); }
  }
  useEffect(() => () => stopVoicePreview(false), []);
  async function previewVoice(targetVoice: string, voiceSequence: number) {
    if (previewingVoice === targetVoice && !previewLoading) { stopVoicePreview(); return; }
    stopVoicePreview();
    const requestId = voicePreviewRequestRef.current;
    setPreviewingVoice(targetVoice); setPreviewLoading(true); setVoicePreviewError("");
    try {
      const blob = await apiBlob("/human/voice-preview", { method: "POST", body: JSON.stringify({ voice_sequence: voiceSequence }) });
      if (requestId !== voicePreviewRequestRef.current) return;
      const url = URL.createObjectURL(blob); const player = new Audio(url);
      voiceAudioUrlRef.current = url; voicePlayerRef.current = player; setPreviewLoading(false);
      player.onended = () => { if (voicePlayerRef.current === player) stopVoicePreview(); };
      await player.play();
    } catch (reason) {
      if (requestId === voicePreviewRequestRef.current) { stopVoicePreview(); setVoicePreviewError(reason instanceof Error ? reason.message : "音色试听失败"); }
    }
  }
  function stopNarration(updateState = true) {
    if (narrationPlayerRef.current) { narrationPlayerRef.current.pause(); narrationPlayerRef.current.currentTime = 0; narrationPlayerRef.current = null; }
    if (narrationAudioUrlRef.current) { URL.revokeObjectURL(narrationAudioUrlRef.current); narrationAudioUrlRef.current = ""; }
    if (updateState) setPlayingNarrationId("");
  }
  useEffect(() => () => stopNarration(false), []);
  async function listenNarration(item: Narration) {
    if (playingNarrationId === item.id) { stopNarration(); return; }
    stopNarration(); stopVoicePreview(); setPlayingNarrationId(item.id);
    try {
      const blob = await apiBlob(`/human/narrations/${item.id}/audio`); const url = URL.createObjectURL(blob); const player = new Audio(url);
      narrationAudioUrlRef.current = url; narrationPlayerRef.current = player;
      player.onended = () => { if (narrationPlayerRef.current === player) stopNarration(); };
      await player.play();
    } catch { stopNarration(); }
  }
  const loadHistory = useCallback(async (page: number) => {
    const result = await api<{ total: number; items: CopyAnalysis[] }>(`/human/copies/iterations?page=${page}&page_size=10`);
    setHistory(result.items); setHistoryTotal(result.total);
    return result;
  }, []);
  const generationOperation = usePersistentOperation("copy_generation", async state => {
    if (state.status === "completed") {
      const result = await loadHistory(1);
      setHistoryPage(1);
      setActiveRecord(result.items[0] ?? null);
      setGenerationNotice(state.detail || "文案生成已完成。");
      await reload();
    } else {
      setGenerationError(state.detail || "文案分析与生成未完成");
    }
  });
  useEffect(() => { loadHistory(historyPage).catch(() => undefined); }, [historyPage, loadHistory]);
  function replaceRecord(record: CopyAnalysis) {
    setActiveRecord(record); setHistory(rows => rows.map(item => item.id === record.id ? record : item));
  }
  async function generateCopies(event: FormEvent) {
    event.preventDefault();
    const operationId = generationOperation.begin();
    if (!operationId) return;
    setGenerationError(""); setGenerationNotice(""); setActiveRecord(null);
    try {
      const record = await api<CopyAnalysis>("/human/copies/iterations", { method: "POST", headers: { "X-Operation-Id": operationId }, body: JSON.stringify({ reference_text: reference }) });
      setActiveRecord(record); setHistoryPage(1); await Promise.all([loadHistory(1), reload()]);
    } catch (reason) {
      setGenerationError(reason instanceof Error ? reason.message : "文案分析与生成失败");
    } finally { generationOperation.clear(operationId); }
  }
  async function review(record: CopyAnalysis, item: CopyCandidate, status: "adopted" | "not_adopted") {
    let reason = "";
    if (status === "not_adopted") { reason = window.prompt("请填写不采纳原因，后续迭代会据此改进")?.trim() ?? ""; if (!reason) return; }
    const ok = await act(() => api(`/human/copies/${item.id}/review`, { method: "PATCH", body: JSON.stringify({ status, reason }) }), status === "adopted" ? "文案已采纳并加入内容文库" : "已记录不采纳原因");
    if (!ok) return;
    replaceRecord({ ...record, batches: record.batches.map(batch => ({ ...batch, copies: batch.copies.map(copy => copy.id === item.id ? { ...copy, status, rejection_reason: reason } : copy) })) });
  }
  async function continueIteration(record: CopyAnalysis) {
    const operationId = generationOperation.begin();
    if (!operationId) return;
    setGenerationError(""); setGenerationNotice("");
    try { const updated = await api<CopyAnalysis>(`/human/copies/iterations/${record.id}/continue`, { method: "POST", headers: { "X-Operation-Id": operationId } }); replaceRecord(updated); await loadHistory(historyPage); }
    catch (reason) { setGenerationError(reason instanceof Error ? reason.message : "继续迭代失败"); }
    finally { generationOperation.clear(operationId); }
  }
  function AnalysisView({ record }: { record: CopyAnalysis }) {
    const latest = record.batches[record.batches.length - 1];
    const pending = latest?.copies.some(item => item.status === "pending") ?? true;
    const labels: Record<string, string> = { language_style: "语言风格", word_preference: "用词偏好", emotional_tone: "情感基调", appeal_focus: "诉求重点", age: "年龄", gender: "性别", interests: "兴趣", spending_level: "消费水平", psychological_state: "心理状态" };
    return <>
      <div className="copy-analysis-grid"><article><h3>文案感官分析</h3>{Object.entries(record.language_analysis).map(([key, value]) => <p key={key}><b>{labels[key] ?? key}</b><span>{value}</span></p>)}</article><article><h3>目标受众推断</h3>{Object.entries(record.audience_analysis).map(([key, value]) => <p key={key}><b>{labels[key] ?? key}</b><span>{value}</span></p>)}</article><article><h3>模型专家角色</h3><p><span>{record.expert_role}</span></p></article></div>
      <div className="copy-batches">{record.batches.map(batch => <section key={batch.id}><div className="human-card-title"><h3>第 {batch.sequence_number} 轮迭代</h3><span>5 条分别审核</span></div>{batch.copies.map((item, index) => <article className="copy-candidate" key={item.id}><div><small>{index + 1}</small><b>{item.content}</b>{item.rejection_reason && <em>不采纳原因：{item.rejection_reason}</em>}</div><div>{item.status === "pending" ? <><button onClick={() => review(record, item, "adopted")}>采纳</button><button className="human-secondary" onClick={() => review(record, item, "not_adopted")}>不采纳</button></> : <Pill value={item.status} />}</div></article>)}</section>)}</div>
      <button type="button" className="human-wide" disabled={generationOperation.busy || pending} onClick={() => continueIteration(record)}>{generationOperation.busy ? <LoaderCircle className="spin" /> : <Sparkles />}{pending ? "请先审核本轮全部文案" : generationOperation.busy ? "正在继续迭代 5 条…" : "继续迭代 5 条"}</button>
    </>;
  }
  async function transcribeToCopy(event: FormEvent) {
    event.preventDefault(); setTranscriptionBusy(true); setTranscriptionError("");
    const form = new FormData();
    if (transcriptionFile) form.append("media", transcriptionFile);
    else form.append("share_url", transcriptionLink.trim());
    try {
      const result = await api<{ text: string }>("/human/copies/audio-to-text", { method: "POST", body: form });
      setTranscriptionText(result.text);
    } catch (reason) { setTranscriptionError(reason instanceof Error ? reason.message : "音频转文案失败"); }
    finally { setTranscriptionBusy(false); }
  }
  async function generateNarration() {
    if (narrationBusy || !narrationText.trim() || !selectedCatalogVoice) return;
    setNarrationBusy(true); setNarrationError("");
    try {
      const success = await act(() => api("/human/narrations/model-voice", { method: "POST", body: JSON.stringify({ approved_text: narrationText.trim(), text_source: selectedCopyId ? "model" : "human", voice_sequence: selectedCatalogVoice.sequence }) }), "旁白配音已生成");
      if (!success) setNarrationError("旁白配音生成失败，请查看页面上方的错误提示。");
    } finally { setNarrationBusy(false); }
  }
  return <section className="human-page copy-library-page">
    <div className="material-tabs copy-library-tabs full"><button className={tab === "copies" ? "active" : ""} onClick={() => setTab("copies")}>文案（{copies.length}）</button><button className={tab === "voices" ? "active" : ""} onClick={() => setTab("voices")}>音色库（597）</button><button className={tab === "narrations" ? "active" : ""} onClick={() => setTab("narrations")}>旁白与字幕（{narrations.length}）</button></div>
    {tab === "copies" && <>
      <div className="human-card full"><div className="human-card-title"><h2>音频转文案</h2><span>抖音短链接、本地视频或本地音频</span></div>
        <form className="human-form audio-to-copy-form" onSubmit={transcribeToCopy}><label>抖音视频短链接<textarea value={transcriptionLink} disabled={transcriptionBusy || Boolean(transcriptionFile)} onChange={event => setTranscriptionLink(event.target.value)} placeholder="粘贴抖音分享内容或短链接；与本地文件二选一" /></label><label>本地视频或音频<input type="file" accept="audio/*,video/*" disabled={transcriptionBusy || Boolean(transcriptionLink.trim())} onChange={event => setTranscriptionFile(event.target.files?.[0] ?? null)} /></label><button disabled={transcriptionBusy || (!transcriptionLink.trim() && !transcriptionFile)}>{transcriptionBusy ? <LoaderCircle className="spin" /> : <Upload />}{transcriptionBusy ? "正在转换…" : "转换成文案"}</button>{transcriptionBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>音频正在转换为文案</b><span>系统正在提取音频并调用语音识别模型，完成前请勿重复提交。</span></div></div>}</form>
        {transcriptionError && <div className="copy-generation-progress error" role="alert"><div><b>转换失败</b><span>{transcriptionError}</span></div></div>}
        {transcriptionText && <div className="human-form transcribed-copy-editor"><label>转换结果<textarea value={transcriptionText} onChange={event => setTranscriptionText(event.target.value)} /><small>可修改后保存到内容文库。</small></label><button disabled={!transcriptionText.trim()} onClick={() => act(() => api("/human/copies", { method: "POST", body: JSON.stringify({ content: transcriptionText.trim(), product_id: null }) }), "转换文案已保存到内容文库").then(ok => { if (ok) { setTranscriptionText(""); setTranscriptionLink(""); setTranscriptionFile(null); } })}>保存到内容文库</button></div>}
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>文案分析与迭代</h2><span>自动分析后一次生成 5 条</span></div>
        <form className="human-form copy-generation-form" onSubmit={generateCopies}><label>参考文案<textarea value={reference} onChange={event => setReference(event.target.value)} placeholder="粘贴一条短标题或长口播稿；留空时将根据全局已采纳文案推荐" disabled={generationOperation.busy} /><small>输入内容会自动作为已采纳文案保存；模型保持内容类型和大致长度。</small></label><button disabled={generationOperation.busy}>{generationOperation.busy ? <LoaderCircle className="spin" /> : <Sparkles />}{generationOperation.busy ? "正在分析并生成 5 条…" : reference.trim() ? "分析并迭代 5 条" : "根据已采纳文案推荐"}</button></form>
        {generationOperation.busy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>正在分析语言、受众和专家角色</b><span>刷新页面后仍会保持此状态；分析完成后自动生成 5 条文案，请勿重复提交。</span></div></div>}
        {generationNotice && <div className="copy-generation-progress" role="status"><div><b>生成完成</b><span>{generationNotice}</span></div></div>}
        {generationError && <div className="copy-generation-progress error" role="alert"><div><b>生成失败</b><span>{generationError}</span></div></div>}
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>分析与迭代记录</h2><span>最新在前，每页 10 条</span></div><div className="copy-history-list">{history.map(item => <div className={`copy-history-entry ${activeRecord?.id === item.id ? "expanded" : ""}`} key={item.id}><article><div><b>{item.source_mode === "input" ? item.source_text : "根据全局已采纳文案推荐"}</b><span>{new Date(item.created_at).toLocaleString()} · {item.batches.length} 轮</span><small>{item.expert_role}</small></div><div><button className="human-secondary" aria-expanded={activeRecord?.id === item.id} onClick={() => setActiveRecord(current => current?.id === item.id ? null : item)}>{activeRecord?.id === item.id ? "收起" : "查看"}</button><button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条分析与迭代记录？", message: "只删除分析、专家角色和迭代过程；已进入内容文库的原文和采纳文案会保留。", onConfirm: async () => { const ok = await act(() => api(`/human/copies/iterations/${item.id}`, { method: "DELETE" }), "分析与迭代记录已删除"); if (ok) { if (activeRecord?.id === item.id) setActiveRecord(null); await loadHistory(historyPage); } } })}>删除</button></div></article>{activeRecord?.id === item.id && <section className="copy-history-detail"><AnalysisView record={activeRecord} /></section>}</div>)}</div><div className="resource-pagination"><span>共 {historyTotal} 条，第 {historyPage} 页</span><div><button className="human-secondary" disabled={historyPage <= 1} onClick={() => setHistoryPage(value => value - 1)}>上一页</button><button className="human-secondary" disabled={historyPage * 10 >= historyTotal} onClick={() => setHistoryPage(value => value + 1)}>下一页</button></div></div></div>
      <div className="human-card full"><div className="human-card-title"><h2>文案内容</h2><span>{visibleCopies.length} 条</span></div>
        <div className="simple-resource-list copy-library-list">{visibleCopies.map(item => <article key={item.id}><div>{editingCopyId === item.id ? <textarea autoFocus value={editingCopy} onChange={event => setEditingCopy(event.target.value)} /> : <b>{item.content}</b>}<span>{item.product_name || "全局通用"} · {item.source === "model" ? "模型生成" : item.source === "original" ? "参考原文" : "人工录入"}</span></div><div>{editingCopyId === item.id ? <><button className="human-secondary" onClick={() => setEditingCopyId(null)}>取消</button><button disabled={!editingCopy.trim()} onClick={() => act(() => api(`/human/copies/${item.id}`, { method: "PUT", body: JSON.stringify({ content: editingCopy.trim(), product_id: item.product_id }) }), "文案已修改").then(ok => { if (ok) setEditingCopyId(null); })}>保存</button></> : <><button className="human-secondary" onClick={() => { setEditingCopyId(item.id); setEditingCopy(item.content); }}>修改</button><button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条文案？", message: "文案将从当前内容文库移除；已经生成的剪映草稿仍保留创建时冻结的内容。", onConfirm: async () => { const ok = await act(() => api(`/human/copies/${item.id}`, { method: "DELETE" }), "文案已删除"); if (ok) setHiddenCopyIds(ids => [...ids, item.id]); return ok; } })}>删除</button></>}</div></article>)}</div>
        <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
      </div>
    </>}
    {tab === "voices" && <>
      <div className="human-card full voice-catalog-card"><div className="human-card-title"><h2>音色库</h2><span>qwen-audio-3.0-tts-plus · 官方 597 条基础音色</span></div><div className="voice-catalog-toolbar"><input value={voiceCatalogQuery} onChange={event => { setVoiceCatalogQuery(event.target.value); setVoiceCatalogPage(1); }} placeholder="查询序号、名称、voice 参数、特质、语种或预览文件名" /><select value={voiceCatalogGender} onChange={event => { setVoiceCatalogGender(event.target.value); setVoiceCatalogPage(1); }}><option value="">全部性别</option>{voiceCatalogGenders.map(value => <option key={value} value={value}>{value}</option>)}</select><select value={voiceCatalogAge} onChange={event => { setVoiceCatalogAge(event.target.value); setVoiceCatalogPage(1); }}><option value="">全部年龄</option>{voiceCatalogAges.map(value => <option key={value} value={value}>{value} 岁</option>)}</select><select value={voiceCatalogScenario} onChange={event => { setVoiceCatalogScenario(event.target.value); setVoiceCatalogPage(1); }}><option value="">全部适用场景</option>{voiceCatalogScenarios.map(value => <option key={value} value={value}>{value}</option>)}</select></div><div className="voice-catalog-table-wrap"><table className="voice-catalog-table"><thead><tr><th>序号</th><th>名称</th><th>voice 参数</th><th>性别</th><th>年龄</th><th>特质</th><th>适用场景</th><th>音色试听</th></tr></thead><tbody>{voiceCatalog.map(item => <tr key={item.sequence}><td>{item.sequence}</td><td>{item.name}</td><td><code>{item.voice}</code></td><td>{item.gender}</td><td>{item.age}</td><td>{item.trait}</td><td>{item.scenario}</td><td><button type="button" className="human-secondary" disabled={previewLoading} onClick={() => previewVoice(item.voice, item.sequence)}>{previewLoading && previewingVoice === item.voice ? <LoaderCircle className="spin" /> : <Volume2 />}{previewingVoice === item.voice && !previewLoading ? "停止" : previewLoading && previewingVoice === item.voice ? "准备中" : item.preview_ready ? "试听" : "生成试听"}</button></td></tr>)}</tbody></table></div>{voicePreviewError && <div className="copy-generation-progress error" role="alert"><div><b>试听失败</b><span>{voicePreviewError}</span></div></div>}<div className="resource-pagination"><span>共 {voiceCatalogTotal} 条，第 {voiceCatalogPage} 页</span><div><button className="human-secondary" disabled={voiceCatalogPage <= 1} onClick={() => setVoiceCatalogPage(value => value - 1)}>上一页</button><button className="human-secondary" disabled={voiceCatalogPage * 20 >= voiceCatalogTotal} onClick={() => setVoiceCatalogPage(value => value + 1)}>下一页</button></div></div></div>
    </>}
    {tab === "narrations" && <>
      <div className="human-card full"><div className="human-card-title"><h2>字幕配音</h2><span>手动输入或从内容文库选择，按音色库序号生成</span></div>
        <div className="human-form narration-generation-form"><label>从内容文库选择<div className="copy-autocomplete"><input value={copySearch} disabled={narrationBusy} autoComplete="off" placeholder="输入文案中的关键词查询" onFocus={() => setCopySearchOpen(true)} onChange={event => { setCopySearch(event.target.value); setCopySearchOpen(true); }} onBlur={() => window.setTimeout(() => setCopySearchOpen(false), 120)} />{copySearchOpen && <div className="copy-autocomplete-options">{copySearchBusy ? <span><LoaderCircle className="spin" />正在查询内容文库…</span> : copySuggestions.length ? copySuggestions.map(item => <button type="button" key={item.id} onMouseDown={event => event.preventDefault()} onClick={() => { setSelectedCopyId(item.id); setSelectedNarrationCopy(item); setNarrationText(item.content); setCopySearch(""); setCopySearchOpen(false); }}>{item.content}<small>{item.product_name || "全局通用"} · {item.source === "model" ? "模型生成" : item.source === "original" ? "参考原文" : "人工录入"}</small></button>) : <span>没有匹配的文案</span>}</div>}</div>{selectedNarrationCopy && <span className="selected-copy-summary"><span><b>已选择文案</b>{selectedNarrationCopy.content}</span><button type="button" className="human-secondary" disabled={narrationBusy} onClick={() => { setSelectedCopyId(""); setSelectedNarrationCopy(null); }}>取消选择</button></span>}<small>输入关键词实时查询全部内容文库；不选择时可直接手动填写下方文案。</small></label><label>旁白文案<textarea value={narrationText} disabled={narrationBusy} onChange={event => { setNarrationText(event.target.value); setSelectedCopyId(""); setSelectedNarrationCopy(null); }} /></label><label>音色库序号<input inputMode="numeric" value={voiceSequenceInput} disabled={narrationBusy} onChange={event => setVoiceSequenceInput(event.target.value)} placeholder="输入 1–597" /><small className={voiceSequenceError ? "field-error" : ""}>{voiceSequenceError || (selectedCatalogVoice ? `已选择：${selectedCatalogVoice.sequence} · ${selectedCatalogVoice.name} · ${selectedCatalogVoice.voice}` : "请输入音色库序号")}</small></label><button disabled={narrationBusy || !narrationText.trim() || !selectedCatalogVoice} onClick={generateNarration}>{narrationBusy ? <LoaderCircle className="spin" /> : <Volume2 />}{narrationBusy ? "正在生成旁白配音…" : "生成旁白配音"}</button>{narrationBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>旁白配音正在生成</b><span>系统正在调用字幕配音模型并生成音频与字幕时间轴，完成前请勿重复提交。</span></div></div>}{narrationError && !narrationBusy && <div className="copy-generation-progress error" role="alert"><div><b>生成失败</b><span>{narrationError}</span></div></div>}</div>
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>旁白与字幕库</h2><span>{narrations.length} 条</span></div>
        <div className="simple-resource-list">{narrations.map(item => <article key={item.id}><div><b>{item.approved_text}</b><span>旁白配音 · {item.subtitle_cues.length} 条字幕</span></div><div><Pill value={item.status} /><button className="human-secondary" onClick={() => listenNarration(item)}>{playingNarrationId === item.id ? "停止试听" : "试听"}</button>{item.status !== "approved" && <button onClick={() => act(() => api(`/human/narrations/${item.id}/confirm`, { method: "PUT", body: JSON.stringify({ approved_text: item.approved_text, subtitle_cues: item.subtitle_cues }) }), "旁白与字幕已确认")}>确认</button>}<button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条旁白配音？", message: "将删除旁白记录和音频文件；已经生成的剪映草稿仍保留其创建快照。", onConfirm: async () => { stopNarration(); return act(() => api(`/human/narrations/${item.id}`, { method: "DELETE" }), "旁白配音已删除"); } })}>删除</button></div></article>)}</div>
        <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
      </div>
    </>}
  </section>;
}
