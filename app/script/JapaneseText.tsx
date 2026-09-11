import { Fragment } from "react";
import { displayJapanese } from "./display-text";
import { phraseRuby } from "./phrase-ruby";

// Parse only the source engine's ruby directive; never inject HTML.
export function JapaneseText({text}: {text:string}) {
  const source = phraseRuby(displayJapanese(text));
  const pattern = /\[ruby\s+text=(?:"([^"]*)"|([^\s\]]+))([^\]]*)\]/g;
  const nodes = [];
  let cursor = 0;
  for (let match; (match = pattern.exec(source));) {
    nodes.push(source.slice(cursor, match.index));
    const count = Number(/\bchar=(\d+)/.exec(match[3])?.[1] ?? 1);
    const base = Array.from(source.slice(pattern.lastIndex)).slice(0, count).join("");
    nodes.push(<ruby key={match.index}>{base}<rp>(</rp><rt>{match[1] ?? match[2]}</rt><rp>)</rp></ruby>);
    cursor = pattern.lastIndex + base.length;
    pattern.lastIndex = cursor;
  }
  nodes.push(source.slice(cursor));
  return <Fragment>{nodes}</Fragment>;
}
