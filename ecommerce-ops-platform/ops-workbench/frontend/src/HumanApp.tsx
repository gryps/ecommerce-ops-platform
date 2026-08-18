import { LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { api, clearToken, storedToken } from "./api";
import { Auth } from "./components/Auth";
import { AccountDialog } from "./components/shell/AccountDialog";
import { AppHeader } from "./components/shell/AppHeader";
import { SidebarNav } from "./components/shell/SidebarNav";
import { useAccountDialogState } from "./components/shell/useAccountDialogState";
import { useNavigationState } from "./components/shell/useNavigationState";
import { useWorkbenchData } from "./components/shell/useWorkbenchData";
import { AiVideoProduction } from "./modules/ai-video-production/AiVideoProduction";
import { ImageProduction } from "./modules/image-production/ImageProduction";
import { BusinessModelSettings } from "./modules/model-config/BusinessModelSettings";
import { OperationsCenter } from "./modules/operations/OperationsCenter";
import { RoleCenter } from "./modules/role-centers/RoleCenter";
import { CopyLibrary, DraftProduction, Flow, Materials, MusicLibrary } from "./modules/video-production/VideoProduction";

export default function HumanApp() {
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem("human_sidebar_collapsed") === "1");
  const navigation = useNavigationState();
  const workbench = useWorkbenchData();
  const account = useAccountDialogState({
    user: workbench.user,
    setUser: workbench.setUser,
    setError: workbench.setError,
    setNotice: workbench.setNotice,
  });

  useEffect(() => {
    api<{ initialized: boolean }>("/auth/status", {}, false).then(value => {
      setInitialized(value.initialized);
      if (value.initialized && storedToken()) workbench.refresh();
    }).catch(() => setInitialized(false));
  }, [workbench.refresh]);

  useEffect(() => {
    localStorage.setItem("human_sidebar_collapsed", sidebarCollapsed ? "1" : "0");
  }, [sidebarCollapsed]);

  if (initialized === null) return <main className="human-loading"><LoaderCircle className="spin" /> 正在启动</main>;
  if (!workbench.user) return <Auth initialized={initialized} done={value => { workbench.setUser(value); workbench.refresh(); }} />;

  const operationMessage = workbench.error || workbench.notice || (workbench.loading ? "正在刷新数据" : "空闲");
  const operationTone = workbench.error ? "error" : workbench.loading ? "busy" : workbench.notice ? "success" : "idle";
  const userDisplayName = workbench.user.display_name || workbench.user.username;

  return <div className={`human-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
    <SidebarNav
      sidebarCollapsed={sidebarCollapsed}
      module={navigation.module}
      view={navigation.view}
      imageView={navigation.imageView}
      operationView={navigation.operationView}
      roleModuleTitle={navigation.roleModuleTitle}
      expandedModules={navigation.expandedModules}
      selectedSecondaryOwner={navigation.selectedSecondaryOwner}
      username={workbench.user.username}
      onToggleSidebar={() => setSidebarCollapsed(value => !value)}
      onPrimaryModuleClick={navigation.handlePrimaryModuleClick}
      onSelectRoleModule={navigation.selectRoleModule}
      onSelectOperationView={navigation.selectOperationView}
      onSelectVideoView={navigation.selectVideoView}
      onSelectImageView={navigation.selectImageView}
      onLogout={() => { clearToken(); workbench.setUser(null); }}
    />
    <main>
      <AppHeader
        subtitle={navigation.headerSubtitle}
        title={navigation.activeTitle ?? "模型配置"}
        operationMessage={operationMessage}
        operationTone={operationTone}
        userDisplayName={userDisplayName}
        onOpenAccount={account.openAccount}
      />
      {account.accountOpen && <AccountDialog
        user={workbench.user}
        profileName={account.profileName}
        profilePhone={account.profilePhone}
        currentPassword={account.currentPassword}
        newPassword={account.newPassword}
        confirmPassword={account.confirmPassword}
        accountBusy={account.accountBusy}
        passwordBusy={account.passwordBusy}
        accountMessage={account.accountMessage}
        accountError={account.accountError}
        onClose={() => account.setAccountOpen(false)}
        onProfileNameChange={account.setProfileName}
        onProfilePhoneChange={account.setProfilePhone}
        onCurrentPasswordChange={account.setCurrentPassword}
        onNewPasswordChange={account.setNewPassword}
        onConfirmPasswordChange={account.setConfirmPassword}
        onSaveProfile={account.saveAccountProfile}
        onSavePassword={account.savePassword}
      />}
      {navigation.module === "video" && navigation.view === "flow" && <Flow materials={workbench.materials} copies={workbench.copies} music={workbench.music} drafts={workbench.drafts} />}
      {navigation.module === "video" && navigation.view === "materials" && <Materials products={workbench.products} act={workbench.act} />}
      {navigation.module === "video" && navigation.view === "copy" && <CopyLibrary copies={workbench.copies} narrations={workbench.narrations} act={workbench.act} reload={workbench.refresh} />}
      {navigation.module === "video" && navigation.view === "music" && <MusicLibrary music={workbench.music} act={workbench.act} />}
      {navigation.module === "video" && navigation.view === "production" && <DraftProduction copies={workbench.copies} narrations={workbench.narrations} music={workbench.music} drafts={workbench.drafts} act={workbench.act} />}
      {navigation.module === "aiVideo" && <AiVideoProduction onError={workbench.setError} onNotice={workbench.setNotice} />}
      {navigation.module === "operations" && <OperationsCenter view={navigation.operationView} onError={workbench.setError} onNotice={workbench.setNotice} />}
      {navigation.roleModuleTitle && <RoleCenter module={navigation.module} />}
      {navigation.module === "images" && <ImageProduction view={navigation.imageView} onError={workbench.setError} onNotice={workbench.setNotice} />}
      {navigation.module === "models" && <BusinessModelSettings onError={workbench.setError} onNotice={workbench.setNotice} />}
    </main>
  </div>;
}
