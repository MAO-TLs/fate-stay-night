// Keep technical anchors stable while showing compact reader-facing numbers.
export function referenceLabel(ref: string): string {
  // Multipart scenes namespace anchors by script ID, not visible numbering.
  ref = ref.replace(/^\d{4}-(?=page)/, "");
  const unit = /-unit(\d+)$/.exec(ref);
  return unit ? String(Number(unit[1])) : ref.replace(/^page/, "");
}
