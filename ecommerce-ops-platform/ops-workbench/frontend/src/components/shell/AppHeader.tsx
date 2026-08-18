import { UserCircle } from "lucide-react";

type AppHeaderProps = {
  subtitle: string;
  title: string;
  operationMessage: string;
  operationTone: "error" | "busy" | "success" | "idle";
  userDisplayName: string;
  onOpenAccount: () => void;
};

export function AppHeader({ subtitle, title, operationMessage, operationTone, userDisplayName, onOpenAccount }: AppHeaderProps) {
  return <header>
    <div className="human-title-block"><small>{subtitle}</small><h1>{title}</h1></div>
    <div className={`human-operation-status ${operationTone}`} role={operationTone === "error" ? "alert" : "status"} aria-live="polite">
      <b>操作状态</b><span title={operationMessage}>{operationMessage}</span>
    </div>
    <button type="button" className="human-user-summary" onClick={onOpenAccount}>
      <UserCircle /><span title={userDisplayName}>{userDisplayName}</span>
    </button>
  </header>;
}
