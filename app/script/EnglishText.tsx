// Manuscript emphasis only, not arbitrary Markdown or HTML. Leave unmatched,
// escaped, and doubled asterisks literal; preserve punctuation and line breaks.
export function EnglishText({text}: {text: string}) {
  const pieces = [];
  const emphasis = /(?<![\\*])\*(?![\s*])([^*\n]*?\S)\*(?!\*)/g;
  let cursor = 0;
  for (const match of text.matchAll(emphasis)) {
    pieces.push(text.slice(cursor, match.index));
    pieces.push(<em key={match.index}>{match[1]}</em>);
    cursor = match.index + match[0].length;
  }
  pieces.push(text.slice(cursor));
  return <>{pieces}</>;
}
