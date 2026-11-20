export type Lang = "uz" | "ru";

export function formatPrice(amount: number | string, lang: Lang): string {
  const n = Math.round(Number(amount));
  const grouped = String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${n < 0 ? "-" : ""}${grouped} ${lang === "ru" ? "сум" : "so'm"}`;
}

export const PHONE_RE = /^\+998\d{9}$/;

/** Backend `normalize_phone` bilan bir xil qoida. */
export function normalizePhone(raw: string): string | null {
  const cleaned = raw.replace(/[\s\-()]/g, "");
  let value = cleaned;
  if (/^998\d+$/.test(cleaned)) value = `+${cleaned}`;
  else if (/^\d{9}$/.test(cleaned)) value = `+998${cleaned}`;
  return PHONE_RE.test(value) ? value : null;
}

/** Server vaqti UTC; zona belgisiz kelsa (SQLite) UTC deb o'qiladi. */
export function parseServerDate(iso: string): Date {
  return new Date(/(Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`);
}

export function formatDateTime(iso: string, lang: Lang): string {
  const d = parseServerDate(iso);
  return d.toLocaleString(lang === "ru" ? "ru-RU" : "uz-UZ", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tashkent",
  });
}
