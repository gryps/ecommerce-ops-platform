import { KeyRound, LoaderCircle, X } from "lucide-react";
import type { FormEvent } from "react";
import type { User } from "../../types";

type AccountDialogProps = {
  user: User;
  profileName: string;
  profilePhone: string;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  accountBusy: boolean;
  passwordBusy: boolean;
  accountMessage: string;
  accountError: string;
  onClose: () => void;
  onProfileNameChange: (value: string) => void;
  onProfilePhoneChange: (value: string) => void;
  onCurrentPasswordChange: (value: string) => void;
  onNewPasswordChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;
  onSaveProfile: (event: FormEvent) => void;
  onSavePassword: (event: FormEvent) => void;
};

export function AccountDialog({
  user,
  profileName,
  profilePhone,
  currentPassword,
  newPassword,
  confirmPassword,
  accountBusy,
  passwordBusy,
  accountMessage,
  accountError,
  onClose,
  onProfileNameChange,
  onProfilePhoneChange,
  onCurrentPasswordChange,
  onNewPasswordChange,
  onConfirmPasswordChange,
  onSaveProfile,
  onSavePassword,
}: AccountDialogProps) {
  return <div className="account-dialog-backdrop" role="presentation">
    <section className="account-dialog" role="dialog" aria-modal="true" aria-labelledby="account-dialog-title">
      <div className="account-dialog-title">
        <div><b id="account-dialog-title">当前用户</b><span>{user.username}</span></div>
        <button type="button" className="human-secondary" onClick={onClose}><X />关闭</button>
      </div>
      <form className="account-form" onSubmit={onSaveProfile}>
        <label>姓名<input value={profileName} onChange={event => onProfileNameChange(event.target.value)} maxLength={80} placeholder={user.username} /></label>
        <label>手机号<input value={profilePhone} onChange={event => onProfilePhoneChange(event.target.value)} maxLength={40} placeholder="未填写" /></label>
        <button type="submit" disabled={accountBusy}>{accountBusy && <LoaderCircle className="spin" />}保存用户信息</button>
      </form>
      <form className="account-form password" onSubmit={onSavePassword}>
        <div><KeyRound /><b>更改密码</b></div>
        <label>当前密码<input type="password" value={currentPassword} onChange={event => onCurrentPasswordChange(event.target.value)} required /></label>
        <label>新密码<input type="password" value={newPassword} onChange={event => onNewPasswordChange(event.target.value)} required minLength={10} /></label>
        <label>确认新密码<input type="password" value={confirmPassword} onChange={event => onConfirmPasswordChange(event.target.value)} required minLength={10} /></label>
        <button type="submit" disabled={passwordBusy}>{passwordBusy && <LoaderCircle className="spin" />}确认修改密码</button>
      </form>
      {(accountError || accountMessage) && <p className={`account-dialog-message ${accountError ? "error" : ""}`}>{accountError || accountMessage}</p>}
    </section>
  </div>;
}
