import { FormEvent, useEffect, useRef, useState } from "react";
import { LoaderCircle, Upload } from "lucide-react";
import { api, apiBlob } from "../../api";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import { Pill } from "../../components/Pill";
import type { DeleteConfirmation, MusicResource } from "../../types";

export function MusicLibrary({ music, act }: { music: MusicResource[]; act: (work: () => Promise<unknown>, success: string) => Promise<boolean> }) {
  const [linkName, setLinkName] = useState(""); const [uploadName, setUploadName] = useState(""); const [shareUrl, setShareUrl] = useState(""); const [file, setFile] = useState<File | null>(null);
  const [extractBusy, setExtractBusy] = useState(false); const [uploadBusy, setUploadBusy] = useState(false);
  const [listeningId, setListeningId] = useState(""); const [listeningBusyId, setListeningBusyId] = useState(""); const [listenError, setListenError] = useState("");
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const [tagEditor, setTagEditor] = useState<MusicResource | null>(null); const [tagInput, setTagInput] = useState(""); const [tagSaving, setTagSaving] = useState(false);
  const playerRef = useRef<HTMLAudioElement | null>(null); const audioUrlRef = useRef(""); const playRequestRef = useRef(0);
  function stopListening(updateState = true) {
    playRequestRef.current += 1;
    if (playerRef.current) { playerRef.current.pause(); playerRef.current.currentTime = 0; playerRef.current = null; }
    if (audioUrlRef.current) { URL.revokeObjectURL(audioUrlRef.current); audioUrlRef.current = ""; }
    if (updateState) { setListeningId(""); setListeningBusyId(""); }
  }
  useEffect(() => () => stopListening(false), []);
  async function extract(event: FormEvent) {
    event.preventDefault(); if (extractBusy) return; setExtractBusy(true);
    try {
      const success = await act(() => api("/music-resources/link", { method: "POST", body: JSON.stringify({ name: linkName, share_url: shareUrl, rights_confirmed: true }) }), "短视频音频已提取并入库");
      if (success) { setLinkName(""); setShareUrl(""); }
    } finally { setExtractBusy(false); }
  }
  async function upload(event: FormEvent) {
    event.preventDefault(); if (!file || uploadBusy) return; setUploadBusy(true);
    const form = new FormData(); form.append("music", file); form.append("name", uploadName); form.append("rights_confirmed", "true");
    try {
      const success = await act(() => api("/music-resources/upload", { method: "POST", body: form }), "背景音乐已上传并入库");
      if (success) { setUploadName(""); setFile(null); }
    } finally { setUploadBusy(false); }
  }
  async function listen(item: MusicResource) {
    if (listeningId === item.id) { stopListening(); return; }
    stopListening(); setListenError(""); const requestId = playRequestRef.current; setListeningBusyId(item.id);
    try {
      const blob = await apiBlob(`/music-resources/${item.id}/audio`);
      if (requestId !== playRequestRef.current) return;
      if (!blob.size) throw new Error("音乐文件为空");
      const url = URL.createObjectURL(blob); const player = new Audio();
      player.preload = "auto"; player.volume = 1; player.muted = false; player.src = url;
      audioUrlRef.current = url; playerRef.current = player;
      player.onended = () => { if (playerRef.current === player) stopListening(); };
      player.onerror = () => { if (playerRef.current === player) { setListenError(`“${item.name}”的音频格式无法播放或文件已损坏`); stopListening(); } };
      await player.play();
      if (requestId === playRequestRef.current) { setListeningBusyId(""); setListeningId(item.id); }
    } catch (reason) {
      if (requestId === playRequestRef.current) { setListenError(reason instanceof Error ? `“${item.name}”试听失败：${reason.message}` : `“${item.name}”试听失败`); stopListening(); }
    }
  }
  function editTags(item: MusicResource) { setTagEditor(item); setTagInput(item.custom_tags.join("，")); }
  async function saveTags() {
    if (!tagEditor || tagSaving) return; setTagSaving(true);
    const custom_tags = Array.from(new Set(tagInput.split(/[,，]/).map(value => value.trim()).filter(Boolean)));
    try {
      const success = await act(() => api(`/music-resources/${tagEditor.id}`, { method: "PATCH", body: JSON.stringify({ name: tagEditor.name, custom_tags }) }), "音乐标签已更新");
      if (success) setTagEditor(null);
    } finally { setTagSaving(false); }
  }
  return <section className="human-page music-library-page">
    <div className="human-card"><div className="human-card-title"><h2>短视频链接提取</h2><span>自动分离音频，失败时可改用上传</span></div><form className="human-form" onSubmit={extract}><label>音乐名称<input value={linkName} onChange={event => setLinkName(event.target.value)} /></label><label>短视频分享链接<textarea value={shareUrl} onChange={event => setShareUrl(event.target.value)} required /></label><button disabled={extractBusy}>{extractBusy && <LoaderCircle className="spin" />}{extractBusy ? "正在下载视频并提取音频…" : "提取背景音乐"}</button>{extractBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>背景音乐正在提取</b><span>下载和音频分离可能需要一些时间，完成前请勿重复提交。</span></div></div>}</form></div>
    <div className="human-card"><div className="human-card-title"><h2>上传音乐</h2><span>支持常见音频和含音轨视频</span></div><form className="human-form" onSubmit={upload}><label>音乐名称<input value={uploadName} disabled={uploadBusy} onChange={event => setUploadName(event.target.value)} /></label><label>音频文件<input type="file" accept="audio/*,video/mp4,video/quicktime" disabled={uploadBusy} onChange={event => setFile(event.target.files?.[0] ?? null)} required /></label><button disabled={uploadBusy}><Upload />{uploadBusy ? "正在上传并处理…" : "上传到背景音乐"}</button>{uploadBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>背景音乐正在上传并处理</b><span>系统正在读取媒体并提取有效音轨，完成前请勿重复提交。</span></div></div>}</form></div>
    <div className="human-card full"><div className="human-card-title"><h2>背景音乐库</h2><span>可试听、自定义标签和删除</span></div>{listenError && <div className="copy-generation-progress error" role="alert"><div><b>音乐试听失败</b><span>{listenError}</span></div></div>}<div className="music-resource-grid">{music.map(item => <article key={item.id}><div><b>{item.name}</b><span>{item.duration_seconds.toFixed(1)} 秒 · {item.source_type === "share_link" ? "链接提取" : "上传"}</span><div>{item.custom_tags.map(tag => <small key={tag}>{tag}</small>)}</div>{item.error && <em>{item.error}</em>}</div><Pill value={item.status} /><div><button className="human-secondary" aria-pressed={listeningId === item.id} disabled={item.status !== "ready" || Boolean(listeningBusyId && listeningBusyId !== item.id)} onClick={() => listen(item)}>{listeningBusyId === item.id ? <><LoaderCircle className="spin" />加载中</> : listeningId === item.id ? "停止试听" : "试听"}</button><button className="human-secondary" onClick={() => editTags(item)}>标签</button><button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条背景音乐？", message: `将删除“${item.name}”的音乐记录和音频文件；如果已被剪映草稿引用，系统会阻止删除。`, onConfirm: async () => { if (listeningId === item.id || listeningBusyId === item.id) stopListening(); return act(() => api(`/music-resources/${item.id}`, { method: "DELETE" }), "背景音乐已删除"); } })}>删除</button></div></article>)}</div>{tagEditor && <div className="confirm-dialog-backdrop" role="presentation"><section className="confirm-dialog music-tag-dialog" role="dialog" aria-modal="true" aria-labelledby="music-tag-title"><div><b id="music-tag-title">设置背景音乐标签</b><span>“{tagEditor.name}”</span><label>音乐标签<input autoFocus value={tagInput} onChange={event => setTagInput(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); saveTags(); } }} placeholder="例如：轻快，治愈，产品展示" /><small>多个标签使用逗号分隔，清空后保存可移除全部标签。</small></label></div><div><button type="button" className="human-secondary" disabled={tagSaving} onClick={() => setTagEditor(null)}>取消</button><button type="button" className="music-tag-confirm" disabled={tagSaving} onClick={saveTags}>{tagSaving && <LoaderCircle className="spin" />}{tagSaving ? "正在保存…" : "保存标签"}</button></div></section></div>}<ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} /></div>
  </section>;
}
