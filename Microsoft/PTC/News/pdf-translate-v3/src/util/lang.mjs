// 언어 코드 정규화. ppt-translate-v4 와 동일한 표기법.
// 입력: en/EN/eng, kr/KR/ko/Korean, ch/zh, jp/ja 등
// 정규화 출력 (cfg 내부 표기): en, kr, ch, jp

const NORMALIZE = {
    en: 'en', english: 'en', eng: 'en',
    kr: 'kr', ko: 'kr', korean: 'kr', kor: 'kr',
    ch: 'ch', zh: 'ch', chinese: 'ch', chs: 'ch', cht: 'ch', cn: 'ch',
    jp: 'jp', ja: 'jp', japanese: 'jp', jpn: 'jp',
};

const LANG_NAME = {
    en: 'English',
    kr: 'Korean',
    ch: 'Chinese',
    jp: 'Japanese',
};

const LANG_SUFFIX = {
    en: 'EN',
    kr: 'KR',
    ch: 'CH',
    jp: 'JP',
};

// PDF /Lang 메타데이터에 들어갈 BCP-47 태그 (정보용; 현재 v1 엔진은 사용하지 않음)
const LANG_TAG = {
    en: 'en',
    kr: 'ko',
    ch: 'zh',
    jp: 'ja',
};

export function normalizeLang(value) {
    const key = String(value || '').trim().toLowerCase();
    return NORMALIZE[key] || key;
}

export function langName(code) {
    return LANG_NAME[code] || code;
}

export function langSuffix(code) {
    return LANG_SUFFIX[code] || code.toUpperCase();
}

export function langTag(code) {
    return LANG_TAG[code] || code;
}
