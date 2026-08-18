import { useEffect, useState } from "react";
import type { ImageView, OperationView, PlatformModule, View } from "../../types";
import {
  getActiveTitle,
  getExpandedModule,
  getHeaderSubtitle,
  getRoleModuleTitle,
  roleModules,
  validExpandedModules,
  type ModuleNavItem,
  type ModuleNavKey,
} from "./moduleNavigation";

const validModules: PlatformModule[] = [
  "operations",
  "procurement",
  "hostControl",
  "adPlanning",
  "customerService",
  "warehouse",
  "finance",
  "project",
  "images",
  "aiVideo",
  "models",
  "video",
];

const storedPlatformModule = (): PlatformModule => {
  const stored = localStorage.getItem("platform_module");
  return validModules.includes(stored as PlatformModule) ? stored as PlatformModule : "video";
};

const storedExpandedModules = (module: PlatformModule): ModuleNavKey[] => {
  const stored = localStorage.getItem("platform_expanded_modules");
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) return parsed.filter((key): key is ModuleNavKey => validExpandedModules.includes(key));
    } catch {
      localStorage.removeItem("platform_expanded_modules");
    }
  }
  const initial = getExpandedModule(module);
  return initial ? [initial] : [];
};

export function useNavigationState() {
  const [module, setModule] = useState<PlatformModule>(storedPlatformModule);
  const [view, setView] = useState<View>("flow");
  const [imageView, setImageView] = useState<ImageView>("overview");
  const [operationView, setOperationView] = useState<OperationView>("overview");
  const [expandedModules, setExpandedModules] = useState<ModuleNavKey[]>(() => storedExpandedModules(module));
  const [selectedSecondaryOwner, setSelectedSecondaryOwner] = useState<ModuleNavKey | "">("");

  useEffect(() => {
    localStorage.setItem("platform_module", module);
  }, [module]);

  useEffect(() => {
    localStorage.setItem("platform_expanded_modules", JSON.stringify(expandedModules));
  }, [expandedModules]);

  const handlePrimaryModuleClick = (item: ModuleNavItem) => {
    const hasSecondaryNav = item.key === "operationsCenter" || item.key === "operations" || item.key === "video" || item.key === "images";
    if (hasSecondaryNav) {
      setExpandedModules(current => current.includes(item.key) ? current.filter(key => key !== item.key) : [...current, item.key]);
    } else {
      setExpandedModules([]);
    }
    setSelectedSecondaryOwner("");
    setModule(item.key === "operationsCenter" ? roleModules[0][0] : item.key);
  };

  const selectRoleModule = (owner: ModuleNavKey, key: PlatformModule) => {
    setSelectedSecondaryOwner(owner);
    setModule(key);
  };

  const selectOperationView = (owner: ModuleNavKey, key: OperationView) => {
    setSelectedSecondaryOwner(owner);
    setModule("operations");
    setOperationView(key);
  };

  const selectVideoView = (owner: ModuleNavKey, key: View) => {
    setSelectedSecondaryOwner(owner);
    setModule("video");
    setView(key);
  };

  const selectImageView = (owner: ModuleNavKey, key: ImageView) => {
    setSelectedSecondaryOwner(owner);
    setModule("images");
    setImageView(key);
  };

  return {
    module,
    view,
    imageView,
    operationView,
    expandedModules,
    selectedSecondaryOwner,
    roleModuleTitle: getRoleModuleTitle(module),
    activeTitle: getActiveTitle(module, view, imageView, operationView),
    headerSubtitle: getHeaderSubtitle(module),
    handlePrimaryModuleClick,
    selectRoleModule,
    selectOperationView,
    selectVideoView,
    selectImageView,
  };
}
