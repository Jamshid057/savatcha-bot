import type { Category, Product } from "../api/types";
import type { Lang } from "../lib/format";
import { useApp } from "../store/app";
import ru from "./ru.json";
import uz from "./uz.json";

export const dictionaries: Record<Lang, Record<string, string>> = { uz, ru };

export function translate(
  lang: Lang,
  key: string,
  params?: Record<string, string | number>,
): string {
  let text = dictionaries[lang][key] ?? dictionaries.uz[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) text = text.replaceAll(`{${k}}`, String(v));
  }
  return text;
}

export function useT() {
  const lang = useApp((s) => s.lang);
  return {
    lang,
    t: (key: string, params?: Record<string, string | number>) => translate(lang, key, params),
  };
}

export const nameOf = (o: Category | Product, lang: Lang): string =>
  lang === "ru" ? o.name_ru : o.name_uz;
export const descOf = (p: Product, lang: Lang): string =>
  lang === "ru" ? p.description_ru : p.description_uz;
