import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { fuzzyRows } from "../utils/fuzzy";

export function ClassificationDropdown({ value, options, placeholder, disabled = false, onChange, onSelect }: {
  value: string;
  options: Array<{ id: string; name: string }>;
  placeholder: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSelect: (item: { id: string; name: string }) => void;
}) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? options.slice(0, 50) : fuzzyRows(options, value, item => item.name, 50);
  return <div className="classification-combobox">
    <input value={value} placeholder={placeholder} disabled={disabled} autoComplete="off" onFocus={() => { setOpen(true); setShowAll(false); }} onChange={event => { onChange(event.target.value); setOpen(true); setShowAll(false); }} onBlur={() => {
      const exact = options.find(item => item.name.trim().toLocaleLowerCase() === value.trim().toLocaleLowerCase());
      if (exact) onSelect(exact);
      window.setTimeout(() => setOpen(false), 100);
    }} />
    <button type="button" className="classification-combobox-toggle human-secondary" aria-label="展开下拉列表" aria-expanded={open} disabled={disabled} onMouseDown={event => event.preventDefault()} onClick={() => { setShowAll(true); setOpen(current => !current || !showAll); }}><ChevronDown /></button>
    {open && <div className="classification-combobox-options">
      {rows.map(item => <button type="button" key={item.id} className={item.name === value ? "selected" : ""} onMouseDown={event => event.preventDefault()} onClick={() => { onSelect(item); setOpen(false); setShowAll(false); }}>{item.name}</button>)}
      {rows.length === 0 && <span>没有匹配项，可输入后单独保存</span>}
    </div>}
  </div>;
}
