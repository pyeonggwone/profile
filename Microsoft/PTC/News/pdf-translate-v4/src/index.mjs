#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { Command } from 'commander';
import { loadConfig } from './util/env.mjs';
import { log } from './util/log.mjs';
import {
    runPipeline,
    processFile,
    extractOnly,
    translateOnly,
    applyOnly,
} from './pipeline.mjs';
import { tmImportCsv, tmReset } from './tm/store.mjs';

const program = new Command();

program
    .name('pdf-translate-v4')
    .description('PDF translator with PyMuPDF rebuild output')
    .version('4.0.0');

// 공통 옵션 등록 helper.
function addLangOptions(cmd) {
    return cmd
        .option('--in-lang <code>', 'source language code (en/kr/ch/jp)')
        .option('--out-lang <code>', 'target language code (en/kr/ch/jp)')
        .option('--keep-input', 'do not move source PDF to input/done after success')
        .option('--reset-tm', 'reset Translation Memory before run');
}

// 기본 명령: 인자 없이 input/ 일괄 처리, 또는 PDF 파일 경로를 주면 단일 처리
addLangOptions(
    program
        .argument('[input...]', 'optional PDF file paths; if omitted, scan input/')
        .action(async (inputs, options) => {
            const cfg = loadConfig(options);
            ensureDirs(cfg);
            if (cfg.resetTm) {
                tmReset(cfg.tmDbPath);
                log.info('TM 초기화 완료:', cfg.tmDbPath);
            }
            log.info(`엔진: ${cfg.modelLabel}, ${cfg.sourceLang} -> ${cfg.targetLang}`);
            if (Array.isArray(inputs) && inputs.length > 0) {
                let ok = 0;
                let fail = 0;
                let skipped = 0;
                for (const file of inputs) {
                    const absolute = path.resolve(file);
                    if (!fs.existsSync(absolute)) {
                        log.error(`입력 파일 없음: ${absolute}`);
                        fail += 1;
                        continue;
                    }
                    try {
                        const result = await processFile(absolute, cfg);
                        if (result.ok) ok += 1;
                        else if (result.skipped) {
                            skipped += 1;
                            log.warn(`스킵: ${absolute} (${result.reason || 'unknown'})`);
                        } else {
                            fail += 1;
                            log.error(`실패: ${absolute} (${result.reason || 'unknown'})`);
                        }
                    } catch (err) {
                        fail += 1;
                        log.error(`실패: ${absolute}\n${err.stack || err.message}`);
                    }
                }
                log.info(`결과: 성공 ${ok}/${inputs.length}, 스킵 ${skipped}, 실패 ${fail}`);
                if (fail > 0) process.exitCode = 1;
                return;
            }
            const result = await runPipeline(cfg);
            if (result.fail > 0) process.exitCode = 1;
        }),
);

// extract: PDF 에서 segments JSON 만 생성
addLangOptions(
    program
        .command('extract <pdf>')
        .description('extract segments JSON from PDF (write to work/<stem>/segments.json)')
        .action(async (pdf, options) => {
            const cfg = loadConfig(options);
            ensureDirs(cfg);
            const out = await extractOnly(path.resolve(pdf), cfg);
            log.info(`segments 작성: ${out}`);
        }),
);

// translate: segments.json 을 받아 translated.json 작성
addLangOptions(
    program
        .command('translate <segments-json>')
        .description('translate segments.json into translated.json (TM + LLM)')
        .action(async (segmentsJson, options) => {
            const cfg = loadConfig(options);
            ensureDirs(cfg);
            if (cfg.resetTm) {
                tmReset(cfg.tmDbPath);
                log.info('TM 초기화 완료:', cfg.tmDbPath);
            }
            const out = await translateOnly(path.resolve(segmentsJson), cfg);
            log.info(`translated 작성: ${out}`);
        }),
);

// apply: 원본 PDF + translated.json 으로 출력 PDF 생성
addLangOptions(
    program
        .command('apply <pdf> <translated-json>')
        .description('apply translated.json to source PDF (incremental update)')
        .action(async (pdf, translatedJson, options) => {
            const cfg = loadConfig(options);
            ensureDirs(cfg);
            const out = await applyOnly(path.resolve(pdf), path.resolve(translatedJson), cfg);
            log.info(`출력 PDF: ${out}`);
        }),
);

// tm subcommand
const tm = program.command('tm').description('Translation Memory utilities');

tm.command('import <csv>')
    .description('import legacy translation pairs from CSV (columns: src,tgt[,source_lang,target_lang])')
    .option('--in-lang <code>', 'override source language for rows missing source_lang')
    .option('--out-lang <code>', 'override target language for rows missing target_lang')
    .action((csv, options) => {
        const cfg = loadConfig(options);
        ensureDirs(cfg);
        const count = tmImportCsv(cfg.tmDbPath, path.resolve(csv), cfg.sourceLang, cfg.targetLang, cfg.modelLabel);
        log.info(`TM import 완료: ${count} 행`);
    });

tm.command('reset')
    .description('delete the entire TM database')
    .action(() => {
        const cfg = loadConfig({});
        tmReset(cfg.tmDbPath);
        log.info('TM 초기화 완료:', cfg.tmDbPath);
    });

function ensureDirs(cfg) {
    for (const dir of [cfg.workDir, cfg.outputDir, cfg.inputDir, cfg.doneDir]) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

program.parseAsync(process.argv).catch((err) => {
    log.error(err.stack || err.message);
    process.exit(1);
});
