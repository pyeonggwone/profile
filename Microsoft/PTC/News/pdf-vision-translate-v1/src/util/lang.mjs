const LANGS = {
    en: { name: 'English', suffix: 'EN', tag: 'en' },
    kr: { name: 'Korean', suffix: 'KR', tag: 'ko' },
    ko: { name: 'Korean', suffix: 'KR', tag: 'ko' },
    jp: { name: 'Japanese', suffix: 'JP', tag: 'ja' },
    ja: { name: 'Japanese', suffix: 'JP', tag: 'ja' },
    ch: { name: 'Chinese', suffix: 'CH', tag: 'zh' },
    zh: { name: 'Chinese', suffix: 'CH', tag: 'zh' },
};

export function normalizeLang(value) {
    const key = String(value || '').trim().toLowerCase();
    if (!key) return 'en';
    if (key === 'korean') return 'kr';
    if (key === 'japanese') return 'jp';
    if (key === 'chinese') return 'ch';
    return LANGS[key] ? key : key;
}

export function langName(value) {
    const lang = LANGS[normalizeLang(value)];
    return lang ? lang.name : value;
}

export function langSuffix(value) {
    const lang = LANGS[normalizeLang(value)];
    return lang ? lang.suffix : String(value || '').toUpperCase();
}

export function langTag(value) {
    const lang = LANGS[normalizeLang(value)];
    return lang ? lang.tag : normalizeLang(value);
}
