import type { PlatformModule } from "../../types";
import { ROLE_CENTERS } from "./roleCenterConfig";

export function RoleCenter({ module }: { module: PlatformModule }) {
  const config = ROLE_CENTERS[module];
  if (!config) return null;
  return <section className="human-page role-center-page">
    <div className="role-center-header">
      <div><small>{config.owner}</small><h2>{config.title}</h2><p>{config.subtitle}</p></div>
      <strong>{config.automation}</strong>
    </div>
    <div className="role-center-grid">
      <div className="human-card">
        <div className="human-card-title"><h2>工作范围</h2><span>岗位负责的业务对象</span></div>
        <div className="role-chip-grid">{config.scope.map(item => <article key={item}>{item}</article>)}</div>
      </div>
      <div className="human-card">
        <div className="human-card-title"><h2>输入</h2><span>进入本中心的数据和凭证</span></div>
        <div className="role-list">{config.inputs.map(item => <p key={item}>{item}</p>)}</div>
      </div>
      <div className="human-card">
        <div className="human-card-title"><h2>输出</h2><span>回写到运营链路的结果</span></div>
        <div className="role-list">{config.outputs.map(item => <p key={item}>{item}</p>)}</div>
      </div>
    </div>
    <div className="human-card">
      <div className="human-card-title"><h2>待部署工作区</h2><span>后续按中心独立扩表、接口和批量作业</span></div>
      <div className="role-workspace-grid">{config.nextWorkspaces.map(item => <button type="button" className="human-secondary" key={item}>{item}</button>)}</div>
    </div>
  </section>;
}
