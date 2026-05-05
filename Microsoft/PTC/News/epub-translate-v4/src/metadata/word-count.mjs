export function countWords(text) {
    const normalized = String(text || '').trim();
    if (!normalized) return 0;
    const wordMatches = normalized.match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu);
    return wordMatches ? wordMatches.length : 0;
}
