import type { Edition } from "./script-labels";

export type PassageText = { ja: string; jaRuby?: string; en: string };
export type EditionPassage = PassageText & {
  editions?: Partial<Record<Edition, PassageText>>;
  availableEditions?: Edition[];
};

export function editionAvailable(page: EditionPassage, edition: Edition): boolean {
  return !page.availableEditions || page.availableEditions.includes(edition);
}

// Project before rendering AND searching: hidden-edition words must not match.
export function editionText<T extends EditionPassage>(page: T, edition: Edition): T {
  const variant = page.editions?.[edition];
  return variant ? {...page, ...variant, jaRuby: variant.jaRuby ?? variant.ja} : page;
}
