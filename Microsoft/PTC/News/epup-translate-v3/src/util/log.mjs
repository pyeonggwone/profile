function ts() {
    return new Date().toISOString().replace('T', ' ').slice(0, 19);
}

function write(level, args) {
    const prefix = `[${ts()}] [${level}]`;
    // eslint-disable-next-line no-console
    console.log(prefix, ...args);
}

export const log = {
    info: (...a) => write('INFO', a),
    warn: (...a) => write('WARN', a),
    error: (...a) => write('ERROR', a),
    debug: (...a) => {
        if (process.env.DEBUG) write('DEBUG', a);
    },
};
