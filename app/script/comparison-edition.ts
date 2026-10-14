import type { Edition } from "./script-labels";

export type Comparison = "mirror-moon" | "remastered";
export function comparisonFor(edition: Edition): Comparison {
  return edition === "all-ages" ? "remastered" : "mirror-moon";
}
export function validComparison(edition: Edition, requested: string | null): boolean {
  return requested === comparisonFor(edition);
}
export const comparisonLabels: Record<Comparison, string> = {
  "mirror-moon": "mirror moon", remastered: "REMASTERED",
};
export type RemasteredRow = {status: string; text: string | null; sourceUnit: string | null};
export type RemasteredPayload = {schema: "fsn-remastered-comparison/1"; scriptId: string; rows: Record<string, RemasteredRow>};
