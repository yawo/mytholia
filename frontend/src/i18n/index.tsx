// i18n context + hook. Provides locale state, a `t` translator, and a
// `locale`/`setLocale` pair to components.
//
// Default locale is French (fr) per the project. The choice is persisted to
// localStorage so it survives reloads. Adding a locale = new file in
// locales/ + a key in the `dictionaries` map here — no component changes.

import { createContext, useContext, useState, type ReactNode } from "react";
import type { Dictionary, Locale } from "./types";
import fr from "./locales/fr";
import en from "./locales/en";

export const dictionaries: Record<Locale, Dictionary> = { fr, en };

const DEFAULT_LOCALE: Locale = "fr";
const STORAGE_KEY = "graphodyssee-locale";

function getInitialLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "fr" || stored === "en") return stored;
  return DEFAULT_LOCALE;
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Dictionary;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale);

  const setLocale = (next: Locale) => {
    setLocaleState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  };

  const value: I18nContextValue = {
    locale,
    setLocale,
    t: dictionaries[locale],
  };

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}

/** Simple placeholder substitution: t("...{count}...", { count: 3 }) → "...3..." */
export function format(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    key in params ? String(params[key]) : `{${key}}`
  );
}
