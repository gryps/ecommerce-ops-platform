const statusText: Record<string, string> = {
  active: "使用中", classified: "已归类", pending: "待审核", adopted: "已采纳",
  not_adopted: "未采纳", approved: "已确认", pending_review: "待确认", ready: "可使用",
  processing: "处理中", failed: "失败", generating: "生成中", disabled: "已停用",
  cancelled: "已终止",
  unreviewed: "未审核", need_redo: "需重做", rejected: "废弃", archived: "已归档",
  needs_reshoot: "素材缺失需重拍",
  waiting_fields: "待填写档案", waiting_auto_fill: "待自动填报", draft_saved: "平台草稿已保存",
};

export function Pill({ value }: { value: string }) {
  return <span className={`human-pill ${value}`}>{statusText[value] ?? value}</span>;
}
