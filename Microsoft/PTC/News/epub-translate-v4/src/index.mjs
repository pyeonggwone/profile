#!/usr/bin/env node
import { Command } from 'commander';
import { loadConfig } from './util/env.mjs';
import { runPipeline } from './pipeline.mjs';
import { log } from './util/log.mjs';

const program = new Command();

program
    .name('epub-translate-v4')
    .description('Native multi-format ebook translator (EPUB, AZW3, MOBI, KFX)')
    .version('4.0.0')
    .option('-i, --input <path>', 'input file or directory')
    .option('-o, --output <dir>', 'output directory')
    .option('-m, --metadata <dir>', 'ebook metadata directory')
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
