import { FormEvent, useState } from "react";
import { LoaderCircle, ShoppingBag } from "lucide-react";
import { api, saveToken } from "../api";
import type { User } from "../types";

export function Auth({ initialized, done }: { initialized: boolean; done: (user: User) => void }) {
  const [setup, setSetup] = useState(!initialized);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (setup) {
        await api("/auth/bootstrap", { method: "POST", body: JSON.stringify({ username, password }) }, false);
        setSetup(false);
        setPassword("");
      } else {
        const result = await api<{ token: string; user: User }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        }, false);
        saveToken(result.token);
        done(result.user);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }
  return <main className="human-auth"><form onSubmit={submit}>
    <div className="human-logo"><ShoppingBag /> 电商运营平台</div>
    <h1>{setup ? "初始化管理员" : "管理员登录"}</h1>
    <label>账号<input value={username} onChange={event => setUsername(event.target.value)} required /></label>
    <label>密码<input type="password" value={password} onChange={event => setPassword(event.target.value)} required minLength={setup ? 10 : 1} /></label>
    {error && <p className="human-error">{error}</p>}
    <button disabled={busy}>{busy && <LoaderCircle className="spin" />}{setup ? "完成初始化" : "登录"}</button>
  </form></main>;
}
