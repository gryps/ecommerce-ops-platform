import {
  BarChart3,
  BookOpenText,
  Boxes,
  CheckCircle2,
  ClipboardList,
  Film,
  Image as ImageIcon,
  Music2,
  Play,
  Settings,
  ShoppingBag,
  Upload,
  WandSparkles,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ImageView, OperationView, PlatformModule, View } from "../../types";

export type ModuleNavKey = PlatformModule | "operationsCenter";
export type SecondaryNavItem<Key extends string> = [Key, string, LucideIcon];
export type ModuleNavItem = {
  key: ModuleNavKey;
  label: string;
  Icon: LucideIcon;
  children?: Array<SecondaryNavItem<PlatformModule>>;
};

export const videoNav: Array<SecondaryNavItem<View>> = [
  ["flow", "生产总览", Film],
  ["materials", "素材归类", Boxes],
  ["copy", "内容文库", BookOpenText],
  ["music", "背景音乐", Music2],
  ["production", "剪映草稿", Play],
];

export const imageNav: Array<SecondaryNavItem<ImageView>> = [
  ["overview", "生产总览", Film],
  ["batches", "拍摄分组", Boxes],
  ["products", "产品资料", BookOpenText],
  ["plans", "出图方案", WandSparkles],
  ["review", "结果审核", CheckCircle2],
  ["delivery", "导出上传", Upload],
];

export const operationNav: Array<SecondaryNavItem<OperationView>> = [
  ["overview", "运营总览", BarChart3],
  ["topology", "业务拓扑", Workflow],
  ["products", "商品库", ShoppingBag],
  ["live", "直播运营", Play],
  ["ads", "投流复盘", ClipboardList],
  ["finance", "库存利润", Boxes],
  ["reports", "日报周报", BookOpenText],
];

export const roleModules: Array<SecondaryNavItem<PlatformModule>> = [
  ["procurement", "采后中心", ShoppingBag],
  ["hostControl", "主播控场", Play],
  ["adPlanning", "投流计划", ClipboardList],
  ["customerService", "客服售后", BookOpenText],
  ["warehouse", "仓库管理", Boxes],
  ["finance", "财务管理", BarChart3],
  ["project", "项目中心", Workflow],
];

export const roleModuleKeys = roleModules.map(([key]) => key);

export const moduleGroups: Array<{ title: string; items: ModuleNavItem[] }> = [
  {
    title: "经营中枢",
    items: [
      { key: "operations", label: "经营看板", Icon: BarChart3 },
      { key: "operationsCenter", label: "运营中心", Icon: Workflow, children: roleModules },
    ],
  },
  {
    title: "内容生产中心",
    items: [
      { key: "images", label: "图片生产", Icon: ImageIcon },
      { key: "video", label: "视频生产", Icon: Film },
      { key: "aiVideo", label: "AI宣传片", Icon: WandSparkles },
    ],
  },
  { title: "系统配置", items: [{ key: "models", label: "模型配置", Icon: Settings }] },
];

export const validExpandedModules: ModuleNavKey[] = ["operations", "operationsCenter", "video", "images"];

export function getExpandedModule(value: PlatformModule): ModuleNavKey | "" {
  if (value === "operations" || value === "video" || value === "images") return value;
  if (roleModuleKeys.includes(value)) return "operationsCenter";
  return "";
}

export function getRoleModuleTitle(value: PlatformModule) {
  return roleModules.find(([key]) => key === value)?.[1];
}

export function getActiveTitle(module: PlatformModule, view: View, imageView: ImageView, operationView: OperationView) {
  if (module === "operations") return operationNav.find(([key]) => key === operationView)?.[1];
  if (module === "video") return videoNav.find(([key]) => key === view)?.[1];
  if (module === "aiVideo") return "AI宣传片";
  if (module === "images") return imageNav.find(([key]) => key === imageView)?.[1];
  return getRoleModuleTitle(module) ?? "模型配置";
}

export function getHeaderSubtitle(module: PlatformModule) {
  if (module === "operations") return "电商运营平台 · 经营看板";
  if (module === "video") return "电商运营平台 · 视频生产";
  if (module === "aiVideo") return "电商运营平台 · AI视频生产";
  if (module === "images") return "电商运营平台 · 图片生产";
  if (module === "models") return "电商运营平台 · 模型配置";
  return `电商运营平台 · 运营中心 · ${getRoleModuleTitle(module)}`;
}
