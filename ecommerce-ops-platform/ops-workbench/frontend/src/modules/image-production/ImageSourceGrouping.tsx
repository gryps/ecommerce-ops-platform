import type { Dispatch, SetStateAction } from "react";
import { LoaderCircle, ShoppingBag, Upload } from "lucide-react";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import type { DeleteConfirmation, ImageSourceAsset } from "../../types";

export function ImageSourceGrouping({
  sourceAssets,
  selectedSourceAssetIds,
  selectedProductName,
  sourceAssetPreviewUrls,
  confirmation,
  busy,
  uploadingSourceAssets,
  setSelectedSourceAssetIds,
  setSelectedProductName,
  setConfirmation,
  uploadSourceAssets,
  createProductFromSourceAssets,
  deleteSourceAsset,
}: {
  sourceAssets: ImageSourceAsset[];
  selectedSourceAssetIds: string[];
  selectedProductName: string;
  sourceAssetPreviewUrls: Record<string, string>;
  confirmation: DeleteConfirmation | null;
  busy: boolean;
  uploadingSourceAssets: boolean;
  setSelectedSourceAssetIds: Dispatch<SetStateAction<string[]>>;
  setSelectedProductName: Dispatch<SetStateAction<string>>;
  setConfirmation: Dispatch<SetStateAction<DeleteConfirmation | null>>;
  uploadSourceAssets: (files: FileList | null) => Promise<void>;
  createProductFromSourceAssets: () => Promise<void>;
  deleteSourceAsset: (asset: ImageSourceAsset) => Promise<void>;
}) {
  return <section className="human-page image-production-page">
    <div className="image-workbench-grid image-batch-stack">
      <div className="human-card"><div className="human-card-title"><h2>人工建档规则</h2><span>只按人工勾选的同款照片创建产品档案</span></div>
        <div className="human-flow image-flow image-selection-rules">{[
          ["1", "按同款选择", "一次选择同一商品的实拍图，选择即形成一个产品组。"],
          ["2", "人工核对", "核对主体、材质、颜色和结构；不按固定张数切分。"],
          ["3", "补拍调整", "补拍图可人工拆分或合并到对应产品组。"],
        ].map(([number, title, detail]) => <article key={number}><i>{number}</i><div><b>{title}</b><span>{detail}</span></div></article>)}</div>
      </div>
      <div className="human-card image-batch-card"><div className="human-card-title"><h2>摄影素材库</h2><span>摄影师上传原始照片；一个产品的照片只能分配到一个产品组</span></div>
        <div className="image-placeholder-upload"><Upload /><b>上传原始照片</b><span>照片会保存到电商运营平台素材库。删除产品档案时，可选择让原图退回待分配区或一并删除。</span><label className="image-upload-button"><Upload />{uploadingSourceAssets ? "正在上传…" : "选择并上传照片"}<input type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" multiple disabled={uploadingSourceAssets} onChange={event => { void uploadSourceAssets(event.target.files); event.currentTarget.value = ""; }} /></label></div>
        <div className="image-next-step">
          <div><b>从待分配素材创建产品组</b><span>勾选同一产品的原始照片，填写唯一产品名称后，系统自动生成产品序列号并创建产品档案。</span></div>
          <div className="image-next-actions"><label className="image-next-product-name">产品名称<input value={selectedProductName} onChange={event => setSelectedProductName(event.target.value)} placeholder="产品名称不可重复" /></label><button type="button" disabled={!selectedSourceAssetIds.length || !selectedProductName.trim() || busy} onClick={createProductFromSourceAssets}>{busy ? <LoaderCircle className="spin" /> : <ShoppingBag />}{busy ? "正在创建…" : "创建产品组"}</button></div>
        </div>
      </div>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>待分配原始照片</h2><span>勾选 {selectedSourceAssetIds.length} 张；已分配照片不会再次出现在此处</span></div>
      <div className="image-source-library">{sourceAssets.filter(asset => asset.status === "unassigned").map(asset => <article key={asset.id} className={selectedSourceAssetIds.includes(asset.id) ? "selected" : ""}><label><input type="checkbox" checked={selectedSourceAssetIds.includes(asset.id)} onChange={event => setSelectedSourceAssetIds(ids => event.target.checked ? [...ids, asset.id] : ids.filter(id => id !== asset.id))} /><span>选择</span></label>{sourceAssetPreviewUrls[asset.id] ? <img src={sourceAssetPreviewUrls[asset.id]} alt={asset.name} /> : <div className="image-source-preview-placeholder">加载缩略图</div>}<b title={asset.name}>{asset.name}</b><small>{new Date(asset.created_at).toLocaleString()}</small><button type="button" className="human-danger compact" onClick={() => setConfirmation({ title: `从素材库删除原始照片“${asset.name}”？`, message: "该照片尚未分配给任何产品。确认后会永久删除素材库文件，无法恢复。", onConfirm: () => deleteSourceAsset(asset) })}>删除</button></article>)}{!sourceAssets.some(asset => asset.status === "unassigned") && <p>暂无待分配原始照片，请先由摄影师上传。</p>}</div>
    </div>
    <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
  </section>;
}
