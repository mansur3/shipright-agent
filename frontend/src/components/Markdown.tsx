import { Fragment, type ReactNode } from "react";

/**
 * Small, safe markdown renderer for model answers. No HTML is ever injected: text becomes React nodes.
 * Supports: headings, paragraphs, bullet and numbered lists, tables, code, **bold**, *italic*, `code`.
 */

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const k = `${keyBase}-${i++}`;
    if (tok.startsWith("**")) out.push(<strong key={k} className="text-ink font-semibold">{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={k} className="px-1 py-0.5 rounded bg-canvas border border-line text-[12px] font-mono">{tok.slice(1, -1)}</code>);
    else out.push(<em key={k}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const isTableSep = (l: string) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);
const splitRow = (l: string) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

export default function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;
  const k = () => `b${key++}`;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    // fenced code
    if (line.trim().startsWith("```")) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) buf.push(lines[i++]);
      i++;
      blocks.push(<pre key={k()} className="my-2 p-2.5 rounded bg-canvas border border-line text-[12px] font-mono overflow-x-auto whitespace-pre">{buf.join("\n")}</pre>);
      continue;
    }

    // table
    if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const head = splitRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(splitRow(lines[i++]));
      blocks.push(
        <div key={k()} className="my-2 overflow-x-auto rounded border border-line">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="bg-canvas">{head.map((h, c) => <th key={c} className="px-2.5 py-1.5 text-left text-ink2 font-medium whitespace-nowrap border-b border-line">{inline(h, `th${c}`)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri} className="border-b border-line last:border-0">
                  {r.map((c, ci) => <td key={ci} className="px-2.5 py-1.5 align-top">{inline(c, `td${ri}-${ci}`)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // heading
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      blocks.push(<p key={k()} className="mt-3 mb-1 font-semibold text-ink text-[13px]">{inline(h[2], `h${key}`)}</p>);
      i++;
      continue;
    }

    // lists
    if (/^\s*([-*•]|\d+[.)])\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const items: string[] = [];
      while (i < lines.length && /^\s*([-*•]|\d+[.)])\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*•]|\d+[.)])\s+/, ""));
        i++;
      }
      const Tag = ordered ? "ol" : "ul";
      blocks.push(
        <Tag key={k()} className={`my-1.5 pl-5 space-y-1 ${ordered ? "list-decimal" : "list-disc"} marker:text-ink3`}>
          {items.map((it, ii) => <li key={ii}>{inline(it, `li${key}-${ii}`)}</li>)}
        </Tag>
      );
      continue;
    }

    // paragraph (until blank line or a block start)
    const buf: string[] = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*([-*•]|\d+[.)])\s+)/.test(lines[i]) && !(lines[i].includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1]))) {
      buf.push(lines[i++]);
    }
    blocks.push(
      <p key={k()} className="my-1.5">
        {buf.map((b, bi) => <Fragment key={bi}>{bi > 0 && <br />}{inline(b, `p${key}-${bi}`)}</Fragment>)}
      </p>
    );
  }

  return <div className="text-[13px] leading-relaxed text-ink [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">{blocks}</div>;
}
