import { create } from "zustand";
import type { Lang } from "../lib/format";

const KEY = "savatcha.lang";

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "uz" || saved === "ru") return saved;
  } catch {
    /* localStorage mavjud emas */
  }
  return navigator.language?.startsWith("ru") ? "ru" : "uz";
}

interface AppState {
  lang: Lang;
  setLang: (lang: Lang) => void;
  toast: { id: number; text: string; kind: "ok" | "error" } | null;
  showToast: (text: string, kind?: "ok" | "error") => void;
}

let toastId = 0;

export const useApp = create<AppState>((set) => ({
  lang: initialLang(),
  setLang: (lang) => {
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      /* e'tiborsiz */
    }
    set({ lang });
  },
  toast: null,
  showToast: (text, kind = "ok") => {
    const id = ++toastId;
    set({ toast: { id, text, kind } });
    setTimeout(() => set((s) => (s.toast?.id === id ? { toast: null } : s)), 2500);
  },
}));
