import { useState } from "react";
import type { Period } from "../../api/admin";
import { useT } from "../../i18n";
import { presetRange, type PresetKey } from "../../lib/dates";

export function usePeriod(initial: Exclude<PresetKey, "custom"> = "7d") {
  return useState<{ key: PresetKey; period: Period }>({ key: initial, period: presetRange(initial) });
}

export function PeriodPicker({
  value,
  onChange,
}: {
  value: { key: PresetKey; period: Period };
  onChange: (v: { key: PresetKey; period: Period }) => void;
}) {
  const { t } = useT();
  const presets: [Exclude<PresetKey, "custom">, string][] = [
    ["today", t("a_today")],
    ["7d", t("a_7d")],
    ["30d", t("a_30d")],
  ];
  return (
    <div className="no-print flex flex-wrap items-center gap-2">
      {presets.map(([key, label]) => (
        <button
          key={key}
          className={value.key === key ? "btn px-3 py-2" : "btn-secondary px-3 py-2"}
          onClick={() => onChange({ key, period: presetRange(key) })}
        >
          {label}
        </button>
      ))}
      <input
        type="date"
        className="input w-auto"
        value={value.period.from}
        max={value.period.to}
        onChange={(e) => e.target.value && onChange({ key: "custom", period: { ...value.period, from: e.target.value } })}
      />
      <span className="text-hint">—</span>
      <input
        type="date"
        className="input w-auto"
        value={value.period.to}
        min={value.period.from}
        onChange={(e) => e.target.value && onChange({ key: "custom", period: { ...value.period, to: e.target.value } })}
      />
    </div>
  );
}
