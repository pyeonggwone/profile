import * as epub from './epub/adapter.mjs';
import * as azw3 from './azw3/adapter.mjs';
import * as mobi from './mobi/adapter.mjs';
import * as kfx from './kfx/adapter.mjs';

const ADAPTERS = { epub, azw3, mobi, kfx };

export function adapterFor(format) {
    const adapter = ADAPTERS[format];
    if (!adapter) throw new Error(`지원하지 않는 포맷 adapter: ${format}`);
    return adapter;
}
