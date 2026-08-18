import { LogOut, PanelLeftClose, PanelLeftOpen, ShoppingBag } from "lucide-react";
import type { ImageView, OperationView, PlatformModule, View } from "../../types";
import {
  imageNav,
  moduleGroups,
  operationNav,
  roleModules,
  videoNav,
  type ModuleNavItem,
  type ModuleNavKey,
} from "./moduleNavigation";

type SidebarNavProps = {
  sidebarCollapsed: boolean;
  module: PlatformModule;
  view: View;
  imageView: ImageView;
  operationView: OperationView;
  roleModuleTitle?: string;
  expandedModules: ModuleNavKey[];
  selectedSecondaryOwner: ModuleNavKey | "";
  username: string;
  onToggleSidebar: () => void;
  onPrimaryModuleClick: (item: ModuleNavItem) => void;
  onSelectRoleModule: (owner: ModuleNavKey, key: PlatformModule) => void;
  onSelectOperationView: (owner: ModuleNavKey, key: OperationView) => void;
  onSelectVideoView: (owner: ModuleNavKey, key: View) => void;
  onSelectImageView: (owner: ModuleNavKey, key: ImageView) => void;
  onLogout: () => void;
};

export function SidebarNav({
  sidebarCollapsed,
  module,
  view,
  imageView,
  operationView,
  roleModuleTitle,
  expandedModules,
  selectedSecondaryOwner,
  username,
  onToggleSidebar,
  onPrimaryModuleClick,
  onSelectRoleModule,
  onSelectOperationView,
  onSelectVideoView,
  onSelectImageView,
  onLogout,
}: SidebarNavProps) {
  const renderSecondaryNav = (owner: ModuleNavItem) => {
    if (!expandedModules.includes(owner.key)) return null;
    if (owner.key === "operationsCenter") {
      return <nav className="platform-secondary-nav">{roleModules.map(([key, label, Icon]) => (
        <button key={key} title={sidebarCollapsed ? label : undefined} className={selectedSecondaryOwner === owner.key && module === key ? "active" : ""} onClick={() => onSelectRoleModule(owner.key, key)}>
          <Icon /><span>{label}</span>
        </button>
      ))}</nav>;
    }
    if (owner.key === "operations") {
      return <nav className="platform-secondary-nav">{operationNav.map(([key, label, Icon]) => (
        <button key={key} title={sidebarCollapsed ? label : undefined} className={selectedSecondaryOwner === owner.key && operationView === key ? "active" : ""} onClick={() => onSelectOperationView(owner.key, key)}>
          <Icon /><span>{label}</span>
        </button>
      ))}</nav>;
    }
    if (owner.key === "video") {
      return <nav className="platform-secondary-nav">{videoNav.map(([key, label, Icon]) => (
        <button key={key} title={sidebarCollapsed ? label : undefined} className={selectedSecondaryOwner === owner.key && view === key ? "active" : ""} onClick={() => onSelectVideoView(owner.key, key)}>
          <Icon /><span>{label}</span>
        </button>
      ))}</nav>;
    }
    if (owner.key === "images") {
      return <nav className="platform-secondary-nav">{imageNav.map(([key, label, Icon]) => (
        <button key={key} title={sidebarCollapsed ? label : undefined} className={selectedSecondaryOwner === owner.key && imageView === key ? "active" : ""} onClick={() => onSelectImageView(owner.key, key)}>
          <Icon /><span>{label}</span>
        </button>
      ))}</nav>;
    }
    return null;
  };

  return <aside>
    <div className="human-brand"><ShoppingBag /><span>电商运营平台<small>Commerce Operations</small></span></div>
    <button type="button" className="human-sidebar-toggle" onClick={onToggleSidebar}>
      {sidebarCollapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
    </button>
    <div className="platform-module-switch" aria-label="业务模块">
      {moduleGroups.map(group => <section className="platform-module-group" key={group.title}>
        <div className="platform-module-group-title">{group.title}</div>
        {group.items.map(item => <div className="platform-module-item" key={item.key}>
          <button type="button" title={sidebarCollapsed ? item.label : undefined} className={module === item.key || (item.key === "operationsCenter" && !!roleModuleTitle) ? "active" : ""} onClick={() => onPrimaryModuleClick(item)}>
            <item.Icon /><span>{item.label}</span>
          </button>
          {renderSecondaryNav(item)}
        </div>)}
      </section>)}
    </div>
    <button className="human-logout" onClick={onLogout}><LogOut /><span>退出 {username}</span></button>
  </aside>;
}
