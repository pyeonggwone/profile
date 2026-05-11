#!/usr/bin/env node
import { Command } from 'commander';
import { loadConfig } from './util/env.mjs';
import { runPipeline } from './pipeline.mjs';
import { log } from './util/log.mjs';

const program = new Command();
program
    .name('epup-translate')
    .description('EPUB 포맷 보존 번역기 (JSZip + parse5 + OpenAI/Azure)')
    .version('3.0.0')
    .action(async () => {
        const cfg = loadConfig();
        log.info(`엔진: ${cfg.modelLabel}, ${cfg.sourceLang} → ${cfg.targetLang}`);
        const r = await runPipeline(cfg);
        if (r.fail > 0) process.exitCode = 1;
    });

program.parseAsync(process.argv).catch((err) => {
    log.error(err.stack || err.message);
    process.exit(1);
});
