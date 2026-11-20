const fmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tashkent" });

/** Toshkent vaqti bo'yicha YYYY-MM-DD */
export const todayTashkent = (): string => fmt.format(new Date());

export function shiftDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export type PresetKey = "today" | "7d" | "30d" | "custom";

export function presetRange(key: Exclude<PresetKey, "custom">, today = todayTashkent()) {
  const days = key === "today" ? 0 : key === "7d" ? 6 : 29;
  return { from: shiftDays(today, -days), to: today };
}

export const shortDay = (iso: string): string => iso.slice(5).replace("-", ".");
