// The game positions incantation readings over individual Latin letters.
// Merge only Latin-text runs with multiple ruby directives, not Japanese prose.
export function phraseRuby(source: string): string {
  return source.replace(/(?:\[ruby\s+text=(?:"[^"]*"|[^\s\]]+)[^\]]*\]|[\x20-\x5a\x5c\x5e-\x7e])+/g, run => {
    const readings: string[] = [];
    const base = run.replace(/\[ruby\s+text=(?:"([^"]*)"|([^\s\]]+))[^\]]*\]/g,
      (_, quoted, plain) => {
        readings.push((quoted ?? plain).replace(/[\s\u3000]+/g, ""));
        return "";
      });
    if (readings.length < 2 || !/[A-Za-z]/.test(base)) return run;
    const trimmed = base.trim();
    const leading = base.slice(0, base.length - base.trimStart().length);
    const trailing = base.slice(base.trimEnd().length);
    return leading + `[ruby text="${readings.join("")}" char=${Array.from(trimmed).length}]${trimmed}` + trailing;
  });
}
