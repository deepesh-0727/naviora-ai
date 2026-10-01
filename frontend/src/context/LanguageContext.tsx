import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type Language = 'en' | 'hi' | 'ta' | 'te' | 'es';

const labels: Record<Language, Record<string, string>> = {
  en: { settings: 'Settings', language: 'Language', logout: 'Logout', loading: 'Loading...' },
  hi: { settings: 'सेटिंग्स', language: 'भाषा', logout: 'लॉग आउट', loading: 'लोड हो रहा है...' },
  ta: { settings: 'அமைப்புகள்', language: 'மொழி', logout: 'வெளியேறு', loading: 'ஏற்றுகிறது...' },
  te: { settings: 'సెట్టింగ్‌లు', language: 'భాష', logout: 'లాగ్ అవుట్', loading: 'లోడ్ అవుతోంది...' },
  es: { settings: 'Configuración', language: 'Idioma', logout: 'Cerrar sesión', loading: 'Cargando...' },
};

type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => Promise<void>;
  t: (key: string) => string;
};

const LanguageContext = createContext<LanguageContextValue>({
  language: 'en',
  setLanguage: async () => undefined,
  t: (key) => key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>('en');

  useEffect(() => {
    AsyncStorage.getItem('language').then((value) => {
      if (value && value in labels) setLanguageState(value as Language);
    }).catch(() => undefined);
  }, []);

  const setLanguage = async (next: Language) => {
    setLanguageState(next);
    await AsyncStorage.setItem('language', next);
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t: (key) => labels[language][key] || key }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
export const useTranslation = useLanguage;
