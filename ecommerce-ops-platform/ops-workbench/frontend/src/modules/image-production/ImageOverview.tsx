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
      <div className="human-card"><div className="human-card-title"><h2>拍摄要求</h2><span>每个产品建议交付 8–12 张清晰原图，按以下机位和细节拍摄</span></div><div className="image-policy-list">
        <p><b>正面主视图 · 2 张：</b>拍摄一张正面平视图和一张正面略俯视图，完整呈现产品轮廓，主体不要被道具或手部遮挡。</p>
        <p><b>左右 45° · 2 张：</b>分别从产品左前方和右前方斜拍；左前 45° 同时看到正面与左侧，右前 45° 同时看到正面与右侧。</p>
        <p><b>侧面与背面 · 2 张：</b>拍摄一个信息量较大的侧面和完整背面；接口、扣件、固定结构等不能被遮挡。</p>
        <p><b>顶部与底部 · 1–2 张：</b>从正上方和正下方拍摄。若底部没有有效信息，可改拍连接处、扣件或其他关键结构。</p>
        <p><b>材质与细节 · 2–3 张：</b>近距离拍清材质纹理、Logo、文字、花纹、接口及工艺细节，确保对焦准确、文字可辨认。</p>
        <p><b>尺寸或佩戴 · 1–2 张：</b>提供带尺子或已知尺寸参照物的照片；可穿戴商品应补充真人正面和侧面佩戴图，呈现比例、位置与遮挡关系。</p>
        <p><b>背景与光线：</b>使用干净、无杂物的中性背景和柔和均匀光线，避免强反光、过曝、严重阴影及环境杂色映到产品表面。</p>
        <p><b>拍摄一致性：</b>所有照片必须是同一件、同一规格和同一状态的产品；尽量保持相同焦段、色温和摆放状态，不使用美颜、滤镜或拼图。</p>
        <p><b>文件质量：</b>上传未经社交软件压缩的原始文件，产品清晰完整且占画面主体；不要添加水印、边框、贴纸或后期文字。</p>
      </div></div>
      <div className="human-card"><div className="human-card-title"><h2>批次状态</h2><span>后续接入自动批次表</span></div><div className="image-status-stack">
        <article><b>待建产品组</b><span>摄影素材库中尚未分配给产品组的原始照片</span><em>{sourceAssets.filter(item => item.status === "unassigned").length}</em></article>
        <article><b>待出图</b><span>已有产品资料但还未形成生成任务</span><em>{Math.max(0, readyProducts.length - tasks.length)}</em></article>
        <article><b>待审核</b><span>已生成或已记录任务，需要判断是否可用</span><em>{tasks.filter(item => item.review_status === "unreviewed").length}</em></article>
      </div></div>
    </div>
  </section>;
}
