import { useState } from "react";
import { api } from "../../api";
import { ConfirmDeleteDialog } from "../../components/ConfirmDeleteDialog";
import type { DeleteConfirmation, Tag, TagCategory } from "../../types";
import { fuzzyRows } from "../../utils/fuzzy";

export function TagManager({ categories, tags, reload, act }: {
  categories: TagCategory[]; tags: Tag[]; reload: () => Promise<void>;
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
}) {
  const [categoryName, setCategoryName] = useState(""); const [tagName, setTagName] = useState("");
  const [categoryId, setCategoryId] = useState(""); const [page, setPage] = useState(0);
  const [editingCategory, setEditingCategory] = useState<string | null>(null); const [editingTag, setEditingTag] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const scopedTags = tags.filter(tag => !categoryId || tag.category_id === categoryId);
  const shown = scopedTags;
  const run = async (work: () => Promise<unknown>, message: string) => { await act(work, message); await reload(); };
  return <div className="master-tag-column">
    <div className="human-card"><div className="human-card-title"><h2>标签分类</h2><span>分类名称可手动输入、查询和选择</span></div>
      <form className="inline-library-form compact" onSubmit={event => { event.preventDefault(); run(() => api("/human/tag-categories", { method: "POST", body: JSON.stringify({ name: categoryName }) }), "标签分类已保存").then(() => setCategoryName("")); }}>
        <input list="master-category-hints" value={categoryName} onChange={event => setCategoryName(event.target.value)} placeholder="输入或查询标签分类" required /><datalist id="master-category-hints">{fuzzyRows(categories, categoryName, item => item.name).map(item => <option key={item.id} value={item.name} />)}</datalist><button>单独保存</button>
      </form>
      <div className="product-manager-list">{categories.slice(0, 20).map(item => <div key={item.id}><span>{editingCategory === item.id ? <input autoFocus value={editName} onChange={event => setEditName(event.target.value)} /> : <b>{item.name}</b>}<small>{tags.filter(tag => tag.category_id === item.id).length} 个标签</small></span><div>{editingCategory === item.id ? <button onClick={() => run(() => api(`/human/tag-categories/${item.id}`, { method: "PATCH", body: JSON.stringify({ name: editName }) }), "标签分类已修改").then(() => setEditingCategory(null))}>保存</button> : <button className="human-secondary" onClick={() => { setEditingCategory(item.id); setEditName(item.name); }}>修改</button>}<button className="human-secondary danger" onClick={() => setConfirmation({ title: `删除标签分类“${item.name}”？`, message: `将同时删除该分类下的 ${tags.filter(tag => tag.category_id === item.id).length} 个标签及视频标签关系。`, onConfirm: () => run(() => api(`/human/tag-categories/${item.id}`, { method: "DELETE" }), "标签分类及其标签已删除") })}>删除</button></div></div>)}</div>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>标签名称</h2><span>同一名称可存在于不同分类</span></div>
      <form className="master-tag-create" onSubmit={event => { event.preventDefault(); run(() => api("/human/tags", { method: "POST", body: JSON.stringify({ category_id: categoryId, name: tagName }) }), "标签已保存").then(() => setTagName("")); }}>
        <select value={categoryId} onChange={event => { setCategoryId(event.target.value); setPage(0); }} required><option value="">选择标签分类</option>{categories.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <input list="master-tag-hints" value={tagName} onChange={event => setTagName(event.target.value)} placeholder="输入或查询标签名称" required /><datalist id="master-tag-hints">{fuzzyRows(tags.filter(item => item.category_id === categoryId), tagName, item => item.name).map(item => <option key={item.id} value={item.name} />)}</datalist><button disabled={!categoryId}>单独保存</button>
      </form>
      <div className="product-library-summary"><span>{categoryId ? `${categories.find(item => item.id === categoryId)?.name ?? ""}分类` : "全部分类"} · {shown.length} 个标签</span></div>
      <div className="product-manager-list">{shown.slice(page * 20, page * 20 + 20).map(tag => <div key={tag.id}><span>{editingTag === tag.id ? <input autoFocus value={editName} onChange={event => setEditName(event.target.value)} /> : <b>{tag.name}</b>}<small>{tag.category}</small></span><div>{editingTag === tag.id ? <button onClick={() => run(() => api(`/human/tags/${tag.id}`, { method: "PATCH", body: JSON.stringify({ name: editName }) }), "标签名称已修改").then(() => setEditingTag(null))}>保存</button> : <button className="human-secondary" onClick={() => { setEditingTag(tag.id); setEditName(tag.name); }}>修改</button>}<button className="human-secondary danger" onClick={() => setConfirmation({ title: `删除标签“${tag.name}”？`, message: `该标签属于“${tag.category}”，删除后将同时移除相关视频标签关系。`, onConfirm: () => run(() => api(`/human/tags/${tag.id}`, { method: "DELETE" }), "标签已删除") })}>删除</button></div></div>)}</div>
      {shown.length > 20 && <div className="resource-pagination"><button className="human-secondary" disabled={page === 0} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page + 1} / {Math.ceil(shown.length / 20)}</span><button className="human-secondary" disabled={(page + 1) * 20 >= shown.length} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
      <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
    </div>
  </div>;
}
