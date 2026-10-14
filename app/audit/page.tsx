import type { Metadata } from "next";
import { AuditReader } from "./AuditReader";

export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "Fate/stay night Translation Audits",
  description: "Japanese-source audits of the mirror moon and REMASTERED English translations of Fate/stay night.",
  alternates: { canonical: "https://mao-tls.github.io/fate-stay-night/audit/" },
};
export default function AuditPage() { return <AuditReader/>; }
