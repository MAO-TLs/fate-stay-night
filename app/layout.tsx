import type { Metadata } from "next";
import "./wa2-publication.css";
import "./mao-reader-template.css";
import "./fate-theme.css";
export const metadata: Metadata = {
  title: { default: "Fate/stay night English Translation | MAO", template: "%s | MAO Translations" },
  description: "Read MAO Translations' Fate/stay night manuscript alongside the original Japanese.",
};
export default function RootLayout({children}: {children: React.ReactNode}) {
 return <html lang="en"><body>{children}</body></html>;
}
