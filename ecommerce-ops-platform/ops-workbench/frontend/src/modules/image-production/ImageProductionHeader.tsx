import type { ImageView } from "../../types";

const copyByView: Record<Exclude<ImageView, "overview" | "batches">, { title: string; description: string }> = {
  products: {
    title: "产品资料",
    description: "管理产品唯一标识、平台模板、自定义字段，并按模板填写或批量修改产品档案。",
  },
  plans: {
    title: "出图方案",
    description: "按产品实拍图生成白底图、环境搭配图、佩戴图和商详图，输出数量按方案自由配置。",
  },
  review: {
    title: "结果审核",
    description: "每个产品下按图片类型审核结果，满意标记可用，不满意填写意见后重做。",
  },
  delivery: {
    title: "导出上传",
    description: "审核通过的结果可以按产品目录导出，也可以按平台模板选图并保存平台草稿。",
  },
};

export function ImageProductionHeader({ view }: { view: Exclude<ImageView, "overview" | "batches"> }) {
  const copy = copyByView[view];
  return (
    <div className="image-ops-header">
      <div>
        <small>Commerce Image Production</small>
        <h2>{copy.title}</h2>
        <p>{copy.description}</p>
      </div>
    </div>
  );
}
