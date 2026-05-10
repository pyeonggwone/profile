export const pageLayoutSchema = {
    name: 'page_layout',
    strict: true,
    schema: {
        type: 'object',
        additionalProperties: false,
        required: ['page', 'width', 'height', 'dpi', 'rotation', 'languageHints', 'blocks', 'warnings'],
        properties: {
            page: { type: 'integer' },
            width: { type: 'integer' },
            height: { type: 'integer' },
            dpi: { type: 'integer' },
            rotation: { type: 'integer' },
            languageHints: { type: 'array', items: { type: 'string' } },
            blocks: { type: 'array', items: { '$ref': '#/$defs/block' } },
            warnings: { type: 'array', items: { type: 'string' } }
        },
        '$defs': {
            bbox: {
                type: 'object',
                additionalProperties: false,
                required: ['x', 'y', 'width', 'height'],
                properties: {
                    x: { type: 'number' },
                    y: { type: 'number' },
                    width: { type: 'number' },
                    height: { type: 'number' }
                }
            },
            style: {
                type: 'object',
                additionalProperties: false,
                required: ['fontSizeApprox', 'bold', 'italic', 'color', 'align', 'backgroundColor'],
                properties: {
                    fontSizeApprox: { type: ['number', 'null'] },
                    bold: { type: ['boolean', 'null'] },
                    italic: { type: ['boolean', 'null'] },
                    color: { type: ['string', 'null'] },
                    align: { type: ['string', 'null'] },
                    backgroundColor: { type: ['string', 'null'] }
                }
            },
            border: {
                type: 'object',
                additionalProperties: false,
                required: ['style', 'thicknessApprox', 'color'],
                properties: {
                    style: { type: ['string', 'null'] },
                    thicknessApprox: { type: ['number', 'null'] },
                    color: { type: ['string', 'null'] }
                }
            },
            cell: {
                type: 'object',
                additionalProperties: false,
                required: ['row', 'column', 'rowSpan', 'columnSpan', 'bbox', 'text', 'backgroundColor', 'align'],
                properties: {
                    row: { type: 'integer' },
                    column: { type: 'integer' },
                    rowSpan: { type: 'integer' },
                    columnSpan: { type: 'integer' },
                    bbox: { '$ref': '#/$defs/bbox' },
                    text: { type: ['string', 'null'] },
                    backgroundColor: { type: ['string', 'null'] },
                    align: { type: ['string', 'null'] }
                }
            },
            table: {
                type: 'object',
                additionalProperties: false,
                required: ['rows', 'columns', 'border', 'cells'],
                properties: {
                    rows: { type: 'integer' },
                    columns: { type: 'integer' },
                    border: { '$ref': '#/$defs/border' },
                    cells: { type: 'array', items: { '$ref': '#/$defs/cell' } }
                }
            },
            block: {
                type: 'object',
                additionalProperties: false,
                required: ['id', 'type', 'role', 'bbox', 'text', 'description', 'containsText', 'readingOrder', 'style', 'table', 'confidence'],
                properties: {
                    id: { type: 'string' },
                    type: { type: 'string', enum: ['text', 'image', 'table', 'shape', 'line', 'unknown'] },
                    role: { type: 'string' },
                    bbox: { '$ref': '#/$defs/bbox' },
                    text: { type: ['string', 'null'] },
                    description: { type: ['string', 'null'] },
                    containsText: { type: ['boolean', 'null'] },
                    readingOrder: { type: ['integer', 'null'] },
                    style: { '$ref': '#/$defs/style' },
                    table: { anyOf: [{ '$ref': '#/$defs/table' }, { type: 'null' }] },
                    confidence: { type: 'number' }
                }
            }
        }
    }
};
