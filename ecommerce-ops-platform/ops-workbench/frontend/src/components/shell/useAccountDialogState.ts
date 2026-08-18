import { FormEvent, useEffect, useState } from "react";
import { api } from "../../api";
import type { User } from "../../types";

type AccountDialogStateOptions = {
  user: User | null;
  setUser: (value: User | null) => void;
  setError: (value: string) => void;
  setNotice: (value: string) => void;
};

export function useAccountDialogState({ user, setUser, setError, setNotice }: AccountDialogStateOptions) {
  const [accountOpen, setAccountOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [profilePhone, setProfilePhone] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [accountBusy, setAccountBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [accountMessage, setAccountMessage] = useState("");
  const [accountError, setAccountError] = useState("");

  useEffect(() => {
    if (!user) return;
    setProfileName(user.display_name || user.username);
    setProfilePhone(user.phone || "");
  }, [user]);

  const openAccount = () => {
    setAccountOpen(true);
    setAccountError("");
    setAccountMessage("");
  };

  async function saveAccountProfile(event: FormEvent) {
    event.preventDefault();
    setAccountBusy(true);
    setAccountError("");
    setAccountMessage("");
    setError("");
    setNotice("");
    try {
      const updated = await api<User>("/auth/me", { method: "PATCH", body: JSON.stringify({ display_name: profileName, phone: profilePhone }) });
      setUser(updated);
      setAccountMessage("用户信息已更新");
      setNotice("用户信息已更新");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "用户信息保存失败";
      setAccountError(message);
      setError(message);
    } finally {
      setAccountBusy(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordBusy(true);
    setAccountError("");
    setAccountMessage("");
    setError("");
    setNotice("");
    if (newPassword !== confirmPassword) {
      setAccountError("两次输入的新密码不一致");
      setPasswordBusy(false);
      return;
    }
    try {
      await api("/auth/me/password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setAccountMessage("密码已更新");
      setNotice("密码已更新");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "密码修改失败";
      setAccountError(message);
      setError(message);
    } finally {
      setPasswordBusy(false);
    }
  }

  return {
    accountOpen,
    setAccountOpen,
    profileName,
    profilePhone,
    currentPassword,
    newPassword,
    confirmPassword,
    accountBusy,
    passwordBusy,
    accountMessage,
    accountError,
    openAccount,
    setProfileName,
    setProfilePhone,
    setCurrentPassword,
    setNewPassword,
    setConfirmPassword,
    saveAccountProfile,
    savePassword,
  };
}
