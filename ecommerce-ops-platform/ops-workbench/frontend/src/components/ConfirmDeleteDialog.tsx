import { useEffect, useState } from "react";
import { LoaderCircle } from "lucide-react";
import type { DeleteConfirmation } from "../types";

export function ConfirmDeleteDialog({ confirmation, close }: { confirmation: DeleteConfirmation | null; close: () => void }) {
  const [deleting, setDeleting] = useState(false);
  useEffect(() => { setDeleting(false); }, [confirmation]);
  if (!confirmation) return null;
  const confirm = async (optionSelected = false) => {
    setDeleting(true);
    try {
      const succeeded = await confirmation.onConfirm(optionSelected);
      if (succeeded !== false) close();
    } finally {
      setDeleting(false);
    }
  };
  return <div className="confirm-dialog-backdrop" role="presentation">
    <section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-delete-title">
      <div className="confirm-dialog-body">
        <b id="confirm-delete-title">{confirmation.title}</b>
        <span>{confirmation.message}</span>
        {confirmation.optionLabel && <small>如果还需要后期重新分配原始照片，请选择保留原图。</small>}
      </div>
      <div className={confirmation.optionLabel ? "confirm-dialog-actions split" : "confirm-dialog-actions"}>
        <button type="button" className="human-secondary" disabled={deleting} onClick={close}>取消</button>
        <button type="button" className="human-danger" disabled={deleting} onClick={() => confirm(false)}>{deleting ? <LoaderCircle className="spin" /> : null}{confirmation.confirmLabel ?? "确认删除"}</button>
        {confirmation.optionLabel && <button type="button" className="human-danger ghost" disabled={deleting} onClick={() => confirm(true)}>{confirmation.optionLabel}</button>}
      </div>
    </section>
  </div>;
}
