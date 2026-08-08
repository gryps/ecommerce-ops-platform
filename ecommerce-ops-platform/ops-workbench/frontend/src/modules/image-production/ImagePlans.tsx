import type { Dispatch, SetStateAction } from "react";
import { Layers, WandSparkles } from "lucide-react";
import type { ImagePrompt, ImageProduct, ImageTemplate } from "../../types";
import { ProductPicker } from "./ProductPicker";

export function ImagePlans({
  products,
  selected,
  selectedId,
  templates,
  currentTemplate,
  templateId,
  model,
  outputPlan,
  prompt,
  busy,
  setSelectedId,
  setTemplateId,
  setModel,
  setOutputPlan,
  setPrompt,
  generatePrompt,
  createTaskFromPrompt,
}: {
  products: ImageProduct[];
  selected: ImageProduct | null;
  selectedId: string;
  templates: ImageTemplate[];
  currentTemplate: ImageTemplate | null;
  templateId: string;
  model: string;
  outputPlan: Record<string, number>;
  prompt: ImagePrompt | null;
  busy: boolean;
  setSelectedId: Dispatch<SetStateAction<string>>;
  setTemplateId: Dispatch<SetStateAction<string>>;
  setModel: Dispatch<SetStateAction<string>>;
  setOutputPlan: Dispatch<SetStateAction<Record<string, number>>>;
  setPrompt: Dispatch<SetStateAction<ImagePrompt | null>>;
  generatePrompt: () => Promise<void>;
  createTaskFromPrompt: () => Promise<void>;
}) {
  return <div className="image-production-layout">
    <ProductPicker products={products} selectedId={selectedId} onSelect={setSelectedId} />
    <div className="image-main-column">
      <div className="human-card">
        <div className="human-card-title"><h2>已确认实拍图</h2><span>来自人工确认的产品组，数量不设固定限制</span></div>
        {selected?.source_images?.length ? <div className="image-source-strip image-product-source-strip">{selected.source_images.map((image, index) => <article key={image.path}><b>{String(index + 1).padStart(2, "0")}</b><span title={image.name}>{image.name}</span><small title={image.relative_path}>{image.relative_path}</small></article>)}</div> : <div className="human-note">当前产品尚未关联实拍图。请先在“拍摄分组”勾选同款原始照片并创建产品组。</div>}
      </div>
      <div className="human-card"><div className="human-card-title"><h2>输出方案</h2><span>随任务保存，数量可自由配置</span></div>
        <div className="image-output-plan">
          {["白底图", "环境搭配图", "佩戴图", "商详图"].map((name, index) => <article key={name}><b>{name}</b><span>{index === 0 ? "主图、规格展示、平台白底要求" : index === 1 ? "场景陈列、氛围搭配、详情辅助" : index === 2 ? "真人或模特佩戴效果" : "卖点、参数、结构和使用场景排版"}</span><input type="number" min="0" max="100" value={outputPlan[name] ?? 0} onChange={event => setOutputPlan(plan => ({ ...plan, [name]: Math.max(0, Number(event.target.value) || 0) }))} /></article>)}
        </div>
      </div>
    </div>
    <aside className="image-side-column">
      <div className="human-card">
        <div className="human-card-title"><h2>提示词模板</h2><span>{templates.length} 个内置模板</span></div>
        <div className="image-template-panel">
          <select value={templateId} onChange={event => { setTemplateId(event.target.value); setPrompt(null); }}>
            {templates.map(item => <option key={item.id} value={item.id}>{item.name} · {item.aspect_ratio}</option>)}
          </select>
          {currentTemplate && <p>{currentTemplate.scene}</p>}
          <input value={model} onChange={event => setModel(event.target.value)} placeholder={currentTemplate ? `推荐：${currentTemplate.recommended_models.join("、")}` : "生成平台"} />
          <button type="button" disabled={!selected || !currentTemplate || busy} onClick={generatePrompt}><WandSparkles />生成提示词</button>
        </div>
        {prompt && <div className="image-prompt-result">
          <textarea readOnly value={prompt.prompt_zh} />
          <div><button type="button" className="human-secondary" onClick={() => navigator.clipboard?.writeText(prompt.prompt_zh)}>复制提示词</button><button type="button" onClick={createTaskFromPrompt}><Layers />记录生成任务</button></div>
        </div>}
      </div>
    </aside>
  </div>;
}
