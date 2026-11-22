"use client";

import { useRef, useState } from "react";
import { apiPost } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import Card from "@/components/Card";
import Markdown from "@/components/Markdown";

interface Message {
  role: "user" | "ai" | "thinking";
  text: string;
  evidence?: { tool: string; summary: string }[];
  model_calls?: number;
  usage?: { input_tokens: number; output_tokens: number; seconds: number; cost_inr_estimate: number; model: string };
  flags?: string[];
  blocked?: boolean;
}

const SUGGESTIONS = [
  "How much have we credited against clear policy rules, and who should recover it?",
  "Which stockists have the highest claim-back rate?",
  "Which C&F has too little stock, and is there spare stock elsewhere?",
  "Is Hooghly dispatching newer batches first?",
  "How many scheme packs come back as claims?",
  "Validate claim STK0054 batch K2310267 50 strips near expiry 15-09-2025",
];

export default function AskPage() {
  const [msgs, setMsgs] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function send(q: string) {
    if (!q.trim() || busy) return;
    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", text: q }, { role: "thinking", text: "Analysing…" }]);
    try {
      const r = await apiPost<AskResponse>("/api/chat/ask", { question: q });
      setMsgs((m) => [
        ...m.slice(0, -1),
        {
          role: "ai",
          text: r.answer,
          evidence: r.evidence,
          model_calls: r.model_calls,
          usage: r.usage ?? undefined,
          flags: r.flags,
          blocked: r.blocked,
        },
      ]);
    } catch (e: unknown) {
      setMsgs((m) => [
        ...m.slice(0, -1),
        { role: "ai", text: `Error: ${e instanceof Error ? e.message : "Request failed"}` },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <Card title="Ask Sankalp AI — grounded in CSV data, not memory">
        <div className="min-h-[360px] max-h-[62vh] overflow-y-auto space-y-3 pb-3">
          {msgs.length === 0 && (
            <p className="text-ink3 text-[13px] text-center pt-10">
              Ask a question about claims, inventory, fill rate, or stockists.<br />
              Every number comes from a tool call against the data files.
            </p>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`${m.role === "ai" ? "w-full" : "max-w-[88%]"} rounded-[10px] px-3.5 py-2.5 text-[13px] leading-relaxed ${
                m.role === "user" ? "bg-brand text-white"
                  : m.role === "thinking" ? "bg-raised border border-line text-ink3 italic opacity-70"
                  : "bg-raised border border-line text-ink"}`}>
                {m.role === "ai" ? <Markdown text={m.text} /> : <p className="whitespace-pre-wrap">{m.text}</p>}
                {m.blocked && (
                  <p className="mt-2 text-[11px] text-danger bg-danger/10 rounded px-2 py-1">
                    ⛔ Request blocked by input guardrail
                  </p>
                )}
                {m.flags && m.flags.length > 0 && (
                  <p className="mt-1.5 text-[11px] text-warn">
                    {m.flags.includes("unverified_number_risk")
                      ? "Some figures were reworded by the model. Open Evidence below and check them against the tool result."
                      : `Guardrail note: ${m.flags.join(", ")}`}
                  </p>
                )}
                {m.evidence && m.evidence.length > 0 && (
                  <details className="mt-2.5 pt-2 border-t border-line text-[11px] text-ink3">
                    <summary className="cursor-pointer select-none hover:text-ink2">
                      Evidence: {m.evidence.length} tool result{m.evidence.length !== 1 ? "s" : ""}
                      {m.model_calls !== undefined && ` · ${m.model_calls} model call${m.model_calls !== 1 ? "s" : ""}`}
                      {m.usage && ` · ${m.usage.input_tokens + m.usage.output_tokens} tokens · ${m.usage.seconds}s · about ₹${m.usage.cost_inr_estimate} (estimate)`}
                    </summary>
                    <ul className="mt-1.5 space-y-1.5">
                      {m.evidence.map((ev, ei) => (
                        <li key={ei}>
                          <span className="font-mono text-ink2">{ev.tool}</span>
                          <span className="block text-ink3 break-words">{ev.summary}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="flex gap-2 mt-3 pt-3 border-t border-line">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about batches, claims, inventory, fill rate…"
            disabled={busy}
            className="flex-1 bg-raised border border-line rounded-sm px-3 py-2 text-[13px] text-ink outline-none focus:border-brand transition-colors disabled:opacity-50"
          />
          <button type="submit" disabled={busy || !input.trim()}
            className="px-4 py-2 bg-brand text-white text-[13px] font-semibold rounded-sm hover:opacity-85 disabled:opacity-50 transition-opacity whitespace-nowrap">
            Ask
          </button>
        </form>

        <div className="flex flex-wrap gap-1.5 mt-3">
          <span className="text-[11px] text-ink3 self-center">Try:</span>
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => send(s)} disabled={busy}
              className="text-[11px] px-2.5 py-1 bg-raised border border-line rounded-full text-ink2 hover:border-brand hover:text-brand transition-colors disabled:opacity-50">
              {s.length > 45 ? s.slice(0, 42) + "…" : s}
            </button>
          ))}
        </div>
      </Card>

      <Card title="How the AI answers — guardrail architecture">
        <div className="text-[13px] text-ink2 space-y-2 leading-relaxed">
          <p>
            <strong className="text-ink">Every number comes from a tool call</strong>, not from the LLM&apos;s training data.
            The LLM decides which tool to call and formats the answer; the tools read the CSV files and
            return exact values.
          </p>
          <p>
            <strong className="text-ink">3 guardrail gates:</strong> (1) Input guard blocks prompt injection
            and off-domain questions before the LLM sees them. (2) Tool guard validates every tool call
            against an allow-list of 11 tools. (3) Output guard scrubs internal paths, keys, and flags
            unverified numbers.
          </p>
          <p className="text-[11px] text-ink3">
            If you try &quot;ignore previous instructions&quot; or &quot;what is the weather&quot; — the input guard
            will block it and explain why.
          </p>
        </div>
      </Card>
    </div>
  );
}
