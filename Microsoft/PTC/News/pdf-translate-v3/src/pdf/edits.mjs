// pdftr EditOperation JSON 직렬화 helper.

const FONT_FAMILIES = new Set(['Helvetica', 'HelveticaBold', 'TimesRoman', 'Courier']);

export const DEFAULT_FONT = 'Helvetica';
export const DEFAULT_FONT_SIZE = 10;
export const DEFAULT_COLOR = [0, 0, 0];
export const WHITE = [1, 1, 1];

export function addText({ page, x, y, text, font = DEFAULT_FONT, size = DEFAULT_FONT_SIZE, color = DEFAULT_COLOR }) {
    if (!FONT_FAMILIES.has(font)) {
        throw new Error(`알 수 없는 FontFamily: ${font}`);
    }
    return {
        type: 'AddText',
        page,
        x: Number(x) || 0,
        y: Number(y) || 0,
        text: String(text || ''),
        font,
        size: Number(size) || DEFAULT_FONT_SIZE,
        color: Array.isArray(color) && color.length === 3
            ? color.map((c) => Number(c) || 0)
            : DEFAULT_COLOR,
    };
}

export function addTextEmbedded({ page, x, y, text, fontPath, size = DEFAULT_FONT_SIZE, color = DEFAULT_COLOR }) {
    if (!fontPath) {
        throw new Error('AddTextEmbedded 에는 fontPath 가 필요합니다.');
    }
    return {
        type: 'AddTextEmbedded',
        page,
        x: Number(x) || 0,
        y: Number(y) || 0,
        text: String(text || ''),
        fontPath: String(fontPath),
        size: Number(size) || DEFAULT_FONT_SIZE,
        color: Array.isArray(color) && color.length === 3
            ? color.map((c) => Number(c) || 0)
            : DEFAULT_COLOR,
    };
}

export function addTextBoxEmbedded({ page, x, y, width, height, text, fontPath, size = DEFAULT_FONT_SIZE, color = DEFAULT_COLOR }) {
    if (!fontPath) {
        throw new Error('AddTextBoxEmbedded 에는 fontPath 가 필요합니다.');
    }
    return {
        type: 'AddTextBoxEmbedded',
        page,
        x: Number(x) || 0,
        y: Number(y) || 0,
        width: Math.max(0, Number(width) || 0),
        height: Math.max(0, Number(height) || 0),
        text: String(text || ''),
        fontPath: String(fontPath),
        size: Number(size) || DEFAULT_FONT_SIZE,
        color: Array.isArray(color) && color.length === 3
            ? color.map((c) => Number(c) || 0)
            : DEFAULT_COLOR,
    };
}

export function addTextAnnotation({ page, x, y, contents }) {
    return {
        type: 'AddTextAnnotation',
        page,
        x: Number(x) || 0,
        y: Number(y) || 0,
        contents: String(contents || ''),
    };
}

export function addFilledRect({ page, x, y, width, height, color = WHITE }) {
    return {
        type: 'FillRect',
        page,
        x: Number(x) || 0,
        y: Number(y) || 0,
        width: Math.max(0, Number(width) || 0),
        height: Math.max(0, Number(height) || 0),
        color: Array.isArray(color) && color.length === 3
            ? color.map((c) => Number(c) || 0)
            : WHITE,
    };
}
