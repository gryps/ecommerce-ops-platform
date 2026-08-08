import type { ClassifiedMaterial, CopyItem, JianyingDraft, MusicResource } from "../../types";

export function Flow({ materials, copies, music, drafts }: { materials: ClassifiedMaterial[]; copies: CopyItem[]; music: MusicResource[]; drafts: JianyingDraft[] }) {
  const steps = [
    ["1", "素材归类", "维护产品与标签，选择原视频后按产品和标签移动重命名，供后续在剪映中手动取用。"],
    ["2", "内容文库", "沉淀已采纳文案，使用音频转文案补充内容，并在旁白与字幕中按音色序号生成可用配音。"],
    ["3", "背景音乐", "上传本地音频或从短视频链接提取音频，试听后维护名称和自定义标签。"],
    ["4", "剪映草稿", "确认剪映草稿目录，选择文案、字幕/旁白和背景音乐，生成无视频轨道的半成品草稿。"],
    ["5", "剪映精修", "打开生成的草稿目录，在剪映专业版中添加视频、裁剪排列并完成后续编辑。"],
  ];
  return <section className="human-page">
    <div className="human-metrics">
      <article><b>{materials.length}</b><span>已归类原视频</span></article>
      <article><b>{copies.length}</b><span>可用内容</span></article>
      <article><b>{music.filter(item => item.status === "ready").length}</b><span>可用背景音乐</span></article>
      <article><b>{drafts.filter(item => item.status === "ready").length}</b><span>剪映草稿</span></article>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>当前生产流程</h2><span>按模块准备物料并生成剪映半成品草稿</span></div>
      <div className="human-flow">{steps.map(([number, title, detail]) => <article key={number}><i>{number}</i><div><b>{title}</b><span>{detail}</span></div></article>)}</div>
    </div>
  </section>;
}
