#!/usr/bin/env node
import { Command } from 'commander';
import { loadConfig } from './util/env.mjs';
import { runPipeline } from './pipeline.mjs';
import { log } from './util/log.mjs';

const program = new Command();

program
    .name('epub-translate-v5')
    .description('EPUB-first ebook translator based on epup-translate-v3')
    .version('5.0.0')
    .option('--format <format>', 'process only one format: epub, azw3, mobi, kfx')
    .action(async (options) => {
        const cfg = loadConfig(options);
        log.info(`엔진: ${cfg.modelLabel}, ${cfg.sourceLang} -> ${cfg.targetLang}`);
        const result = await runPipeline(cfg);
        if (result.fail > 0) process.exitCode = 1;
    });

program.parseAsync(process.argv).catch((err) => {
    log.error(err.stack || err.message);
    process.exit(1);
});