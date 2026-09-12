// Keep technical anchors stable while showing compact reader-facing numbers.
export function referenceLabel(ref: string): string {
  const unit = /-unit(\d+)$/.exec(ref);
  return unit ? String(Number(unit[1])) : ref.replace(/^page/, "");
}
