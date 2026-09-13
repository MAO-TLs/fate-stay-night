import type { Metadata } from "next";
import "./wa2-publication.css";
import "./mao-publication-template.css";
import "./mao-reader-template.css";
import "./fate-theme.css";
export const metadata: Metadata = {
  title: { default: "Fate/stay night English Translation | MAO", template: "%s | MAO Translations" },
  description: "Download the MAO English patch for Fate/stay night Réalta Nua Ultimate Edition, or read both editions beside the Japanese script.",
};
export default function RootLayout({children}: {children: React.ReactNode}) {
 return <html lang="en"><body>{children}</body></html>;
}
