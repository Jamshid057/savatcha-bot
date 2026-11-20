import { useEffect } from "react";

interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

interface TgButton {
  show(): void;
  hide(): void;
  onClick(cb: () => void): void;
  offClick(cb: () => void): void;
}

interface TgMainButton extends TgButton {
  setParams(p: { text?: string; is_visible?: boolean; is_active?: boolean }): void;
  showProgress(): void;
  hideProgress(): void;
}

export interface TgWebApp {
  initData: string;
  themeParams: ThemeParams;
  colorScheme: "light" | "dark";
  ready(): void;
  expand(): void;
  disableVerticalSwipes?(): void;
  onEvent(name: string, cb: () => void): void;
  MainButton: TgMainButton;
  BackButton: TgButton;
  HapticFeedback?: {
    impactOccurred(style: "light" | "medium" | "heavy"): void;
    notificationOccurred(type: "error" | "success" | "warning"): void;
    selectionChanged(): void;
  };
  openLink?(url: string): void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TgWebApp };
  }
}

export const tg = (): TgWebApp | undefined => window.Telegram?.WebApp;

/** Dev rejimida brauzerdan sinash uchun `VITE_DEV_INIT_DATA` ishlatiladi. */
export function getInitData(): string {
  return tg()?.initData || (import.meta.env.VITE_DEV_INIT_DATA as string | undefined) || "";
}

export const isTelegram = (): boolean => Boolean(tg()?.initData);

export function applyTheme(): void {
  const app = tg();
  if (!app) return;
  const p = app.themeParams;
  const root = document.documentElement;
  const set = (name: string, value?: string) => value && root.style.setProperty(name, value);
  set("--c-bg", p.bg_color);
  set("--c-surface", p.secondary_bg_color);
  set("--c-text", p.text_color);
  set("--c-hint", p.hint_color);
  set("--c-link", p.link_color);
  set("--c-accent", p.button_color);
  set("--c-accent-text", p.button_text_color);
  root.classList.toggle("dark", app.colorScheme === "dark");
}

export function initTelegram(): void {
  const app = tg();
  if (!app) return;
  app.ready();
  app.expand();
  app.disableVerticalSwipes?.();
  applyTheme();
  app.onEvent("themeChanged", applyTheme);
}

export const haptic = {
  tap: () => tg()?.HapticFeedback?.impactOccurred("light"),
  select: () => tg()?.HapticFeedback?.selectionChanged(),
  success: () => tg()?.HapticFeedback?.notificationOccurred("success"),
  error: () => tg()?.HapticFeedback?.notificationOccurred("error"),
};

/** Ichki sahifalarda Telegram BackButton ni ko'rsatadi. */
export function useBackButton(visible: boolean, onClick: () => void): void {
  useEffect(() => {
    const btn = tg()?.BackButton;
    if (!btn) return;
    if (!visible) {
      btn.hide();
      return;
    }
    btn.show();
    btn.onClick(onClick);
    return () => {
      btn.offClick(onClick);
      btn.hide();
    };
  }, [visible, onClick]);
}

/** Telegram MainButton; Telegram tashqarisida false qaytaradi (ilova o'z tugmasini chizadi). */
export function useMainButton(opts: {
  text: string;
  onClick: () => void;
  visible?: boolean;
  disabled?: boolean;
  loading?: boolean;
}): boolean {
  const { text, onClick, visible = true, disabled = false, loading = false } = opts;
  const btn = tg()?.MainButton;
  useEffect(() => {
    if (!btn) return;
    btn.setParams({ text, is_visible: visible, is_active: !disabled && !loading });
    if (loading) btn.showProgress();
    else btn.hideProgress();
    btn.onClick(onClick);
    return () => {
      btn.offClick(onClick);
      btn.hide();
    };
  }, [btn, text, onClick, visible, disabled, loading]);
  return Boolean(btn);
}
