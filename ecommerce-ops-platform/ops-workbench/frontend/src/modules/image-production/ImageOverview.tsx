import type { ImageProduct, ImageSourceAsset, ImageTask } from "../../types";

export function ImageOverview({
  products,
  sourceAssets,
  tasks,
  readyProducts,
}: {
  products: ImageProduct[];
  sourceAssets: ImageSourceAsset[];
  tasks: ImageTask[];
  readyProducts: ImageProduct[];
}) {
  const approvedProducts = new Set(tasks.filter(item => item.review_status === "approved").map(item => item.product_id)).size;
  const steps = [
    ["1", "上传摄影素材", "摄影师把原始照片上传到平台素材库，未分配素材可完整预览与删除。"],
    ["2", "人工创建产品组", "勾选同一产品的照片并创建产品组；系统生成不可修改的产品序列号。"],
    ["3", "人工填写产品档案", "在产品资料中新建平台模板和自定义字段，再按产品或批量填写字段值。"],
    ["4", "分析提示词并出图", "分析模型先给出可编辑提示词，再将原图和提示词交给生图模型；任务可终止、删除或重试。"],
    ["5", "审核重做", "每个产品下按图片类型审核，满意标记可用，不满意填写修改意见后重做。"],
    ["6", "导出或上传", "可按产品和图片类型归类导出，也可选择平台模板后由脚本填写字段并上传生成商品链接。"],
  ];

  return <section className="human-page image-production-page">
    <div className="human-metrics">
      <article><b>{products.length}</b><span>图片产品库存</span></article>
      <article><b>{products.reduce((total, item) => total + item.reference_count, 0)}</b><span>已读取实拍图</span></article>
      <article><b>{tasks.length}</b><span>出图处理记录</span></article>
      <article><b>{approvedProducts}</b><span>已有可用结果产品</span></article>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>当前图片生产流程</h2><span>从实拍图到平台商品链接的完整闭环</span></div>
      <div className="human-flow image-flow">{steps.map(([number, title, detail]) => <article key={number}><i>{number}</i><div><b>{title}</b><span>{detail}</span></div></article>)}</div>
    </div>
    <div className="image-dashboard-grid image-overview-stack">
      <div className="human-card"><div className="human-card-title"><h2>业务口径</h2><span>按你确认的实际流程整理</span></div><div className="image-policy-list">
        <p><b>唯一索引：</b>产品编号不可重复，用于防止平台重复上传和导出重名。</p>
        <p><b>人工位置：</b>人工选择同一产品的原始照片、填写产品档案、编辑提示词、审核并选择用于各平台的 AI 图。</p>
        <p><b>交付范围：</b>平台只保存商品草稿；后续检查、修改、发布均在电商平台内完成。</p>
      </div></div>
      <div className="human-card"><div className="human-card-title"><h2>批次状态</h2><span>后续接入自动批次表</span></div><div className="image-status-stack">
        <article><b>待建产品组</b><span>摄影素材库中尚未分配给产品组的原始照片</span><em>{sourceAssets.filter(item => item.status === "unassigned").length}</em></article>
        <article><b>待出图</b><span>已有产品资料但还未形成生成任务</span><em>{Math.max(0, readyProducts.length - tasks.length)}</em></article>
        <article><b>待审核</b><span>已生成或已记录任务，需要判断是否可用</span><em>{tasks.filter(item => item.review_status === "unreviewed").length}</em></article>
      </div></div>
    </div>
  </section>;
}
