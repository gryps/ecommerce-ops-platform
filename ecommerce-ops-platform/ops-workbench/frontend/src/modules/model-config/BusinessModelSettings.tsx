import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { fetchModelList, fetchModelProfiles, saveModelProfile } from "../../api";
import type { ModelProfile } from "../../types";

export function BusinessModelSettings({ onError, onNotice }: { onError: (value: string) => void; onNotice: (value: string) => void }) {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [busy, setBusy] = useState("");
  const [modelLists, setModelLists] = useState<Record<string, string[]>>({});
  useEffect(() => {
    fetchModelProfiles()
      .then(value => setProfiles(value.profiles))
      .catch(reason => onError(reason instanceof Error ? reason.message : "模型配置加载失败"))
      .finally(() => setLoading(false));
  }, [onError]);
  function update(stage: string, values: Partial<ModelProfile>) {
    setProfiles(rows => rows.map(item => item.stage === stage ? { ...item, ...values } : item));
  }
  async function loadModels(profile: ModelProfile) {
    setBusy(profile.stage);
    try {
      const value = await fetchModelList(profile);
      setModelLists(rows => ({ ...rows, [profile.stage]: value.models }));
      if (!value.models.includes(profile.model) && value.models[0]) update(profile.stage, { model: value.models[0] });
      onNotice(profile.stage === "speech_recognition" ? `已读取 ${value.models.length} 个可用于音频转文案的非实时模型` : `已读取 ${value.models.length} 个百炼模型`);
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "连接失败");
    } finally {
      setBusy("");
    }
  }
  async function save(profile: ModelProfile) {
    setSaving(profile.stage);
    try {
      const stored = await saveModelProfile(profile);
      update(profile.stage, stored);
      onNotice(`${profile.label}配置已保存`);
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setSaving("");
    }
  }
  function card(stage: string, description: string) {
    const profile = profiles.find(item => item.stage === stage);
    if (!profile) return null;
    const listed = modelLists[stage] ?? [];
    const options = listed.length ? listed : [profile.model].filter(Boolean);
    const title = profile.label;
    return <article className="human-card business-model-card" key={stage}>
      <div><b>{title}</b><span>{description}</span></div>
      <label>百炼兼容接口<input value={profile.base_url} onChange={event => update(stage, { base_url: event.target.value })} placeholder="https://.../compatible-mode/v1" /></label>
      <label>API Key<input type="password" value={profile.api_key} onChange={event => update(stage, { api_key: event.target.value })} placeholder={profile.api_key_mask || "sk-..."} /></label>
      <label>模型类别{listed.length ? <select value={profile.model} onChange={event => update(stage, { model: event.target.value })}><option value="">请选择模型类别</option>{options.map(value => <option key={value} value={value}>{value}</option>)}</select> : <input value={profile.model} onChange={event => update(stage, { model: event.target.value })} placeholder={stage === "speech_recognition" ? "请填写非实时 qwen3-asr-flash" : stage === "image_analysis" ? "请选择支持图片输入的视觉模型，例如 qwen-vl" : stage === "image_generation" ? "请选择支持参考图生图的模型" : "读取列表后可下拉选择，也可手动填写"} />}</label>
      {stage === "speech_recognition" && <small>仅支持非实时 qwen3-asr-flash；realtime 和 filetrans 使用其他接口，不能用于这里。</small>}
      {stage === "image_analysis" && <small>用于分析产品组原图并为各图类生成可人工编辑的提示词。</small>}
      {stage === "image_generation" && <small>用于接收提示词与原图，生成白底图、环境图、模特图、详情图等 AI 图。</small>}
      <div className="business-model-actions">
        <button type="button" className="human-secondary" disabled={busy === stage || saving === stage || !profile.base_url || (!profile.api_key && !profile.has_api_key)} onClick={() => loadModels(profile)}>{busy === stage && <LoaderCircle className="spin" />}{busy === stage ? "正在读取列表…" : "读取模型列表"}</button>
        <button type="button" disabled={saving === stage || busy === stage} onClick={() => save(profile)}>{saving === stage && <LoaderCircle className="spin" />}{saving === stage ? "正在保存…" : "保存配置"}</button>
      </div>
    </article>;
  }
  if (loading) return <section className="human-page"><div className="human-empty"><LoaderCircle className="spin" />正在加载</div></section>;
  return <section className="human-page business-model-page">
    <div className="human-note"><Sparkles />各业务功能分别配置百炼兼容连接、读取模型列表和保存配置，互不影响。</div>
    <div className="business-model-stack">
      {card("copywriting", "分析语言与受众并生成 5 条文案，也负责字幕文案生成")}
      {card("image_analysis", "分析产品组原图，生成各类 AI 图可人工确认的提示词")}
      {card("image_generation", "接收提示词与原图，生成白底图、环境图、模特图和详情图")}
      {card("speech_recognition", "识别抖音视频、本地视频或本地音频并转换为文案")}
      {card("speech_synthesis", "按音色库序号将文案合成为旁白")}
    </div>
  </section>;
}
