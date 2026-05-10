import { Command } from 'commander';
import { loadConfig } from './util/env.mjs';
import { runAll, renderCommand, analyzeCommand, translateCommand, composeCommand } from './pipeline.mjs';
import { error } from './util/log.mjs';

function addCommonOptions(command) {
    return command
        .option('--in-lang <lang>')
        .option('--out-lang <lang>')
        .option('--reset-work')
        .option('--reset-tm')
        .option('--detail <low|high|original|auto>')
        .option('--dpi <number>')
        .option('--debug');
}

async function main() {
    const program = new Command();
    addCommonOptions(program)
        .name('pdf-vision-translate-v1')
        .argument('[input]', 'PDF file to process')
        .action(async (input, options) => {
            const cfg = loadConfig(options);
            await runAll(cfg, input);
        });

    addCommonOptions(program.command('render'))
        .argument('<input>')
        .action(async (input, options) => renderCommand(loadConfig(options), input));

    addCommonOptions(program.command('analyze'))
        .argument('<input>')
        .action(async (input, options) => analyzeCommand(loadConfig(options), input));

    addCommonOptions(program.command('translate'))
        .argument('<segmentsJson>')
        .action(async (segmentsJson, options) => translateCommand(loadConfig(options), segmentsJson));

    addCommonOptions(program.command('compose'))
        .argument('<inputPdf>')
        .argument('<translatedJson>')
        .action(async (inputPdf, translatedJson, options) => composeCommand(loadConfig(options), inputPdf, translatedJson));

    await program.parseAsync(process.argv);
}

main().catch((err) => {
    error(err?.message || err);
    if (process.env.DEBUG || process.argv.includes('--debug')) console.error(err);
    process.exitCode = 1;
});
