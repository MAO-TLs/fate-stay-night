// Render manuscript blank-line separators as ordinary reader line breaks.
export function displayEnglish(text: string): string {
  return text.replace(/\r?\n(?:[\t ]*\r?\n)+/g, "\n");
}

// Engine/extraction line breaks must not strand Japanese quotation marks.
// Keep the stored corpus and all other paragraph breaks unchanged.
export function displayJapanese(text: string): string {
  return text.replace(/([「『])[\t \u3000]*\r?\n\s*/g, "$1")
    .replace(/\r?\n[\t \u3000]*([」』])/g, "$1");
}
