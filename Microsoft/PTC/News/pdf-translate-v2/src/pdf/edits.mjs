// v1 의 EditOperation::AddText JSON 직렬화 helper.
//
// v1 의 serde tag 는 "type" = "AddText" / "AddTextAnnotation" / "AddImageJpeg".
// FontFamily 는 string enum: "Helvetica" / "HelveticaBold" / "TimesRoman" / "Courier".
// AddText 는 Base14 폰트만 받기 때문에, 한글 등 비-Latin 출력은 v1 의 TrueType 임베딩 API 가
// CLI 표면에 노출되어야 가능하다 (TODO).

const FONT_FAMILIES = new Set(['Helvetica', 'HelveticaBold', 'TimesRoman', 'Courier']);

export const DEFAULT_FONT = 'Helvetica';
export const DEFAULT_FONT_SIZE = 10;
export const DEFAULT_COLOR = [0, 0, 0];

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

export function addTextAnnotation({ page, x, y, contents }) {
    return {
        type: 'AddTextAnnotation',
        page,
        x: Number(x) || 0,
        y: Number(y) || 0,
        contents: String(contents || ''),
    };
}
