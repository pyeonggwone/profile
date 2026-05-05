function ts() {
    return new Date().toISOString().replace('T', ' ').slice(0, 19);
}

function write(level, args) {
    const prefix = `[${ts()}] [${level}]`;
    console.log(prefix, ...args);
}

export const log = {
    info: (...args) => write('INFO', args),
    warn: (...args) => write('WARN', args),
    error: (...args) => write('ERROR', args),
    debug: (...args) => {
        if (process.env.DEBUG) write('DEBUG', args);
    },
};
