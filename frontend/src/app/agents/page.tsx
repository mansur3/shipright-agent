"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import AgentFlow, { Legend } from "@/components/AgentFlow";
import { AGENTS } from "@/lib/agents";

export default function AgentsPage() {
  // ?only=<agent id> shows one agent alone (used to export its diagram)
  const [only, setOnly] = useState("");
  useEffect(() => { setOnly(new URLSearchParams(window.location.search).get("only") ?? ""); }, []);
  const shown = only ? AGENTS.filter((a) => a.id === only) : AGENTS;
  return (
    <div className={only ? "space-y-4" : "space-y-4 max-w-[1400px]"}>
      {!only && <Card title="The agents in Sankalp, and the problem each one solves">
        <p className="text-[13px] text-ink2 leading-relaxed mb-3">
          Rules and money are decided in code. The model only reads a question, picks a tool and explains the result. A named person decides every credit.
          Every figure comes from the findings ledger, with the file and rows behind it.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] border-collapse min-w-[760px]">
            <thead>
              <tr className="border-b border-line text-ink2 text-left">
                <th className="py-2 pr-3 font-medium">Agent</th>
                <th className="py-2 pr-3 font-medium">Type</th>
                <th className="py-2 pr-3 font-medium">Problem it solves</th>
                <th className="py-2 font-medium">Used by</th>
              </tr>
            </thead>
            <tbody>
              {AGENTS.map((a) => (
                <tr key={a.id} className="border-b border-line align-top">
                  <td className="py-2 pr-3 font-semibold whitespace-nowrap"><a href={`#${a.id}`} className="text-brand hover:underline">{a.name}</a></td>
                  <td className="py-2 pr-3 whitespace-nowrap text-ink2">{a.kind}</td>
                  <td className="py-2 pr-3 text-ink2">{a.problem.split(". ")[0]}.</td>
                  <td className="py-2 text-ink3">{a.user}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3"><Legend /></div>
      </Card>}

      {shown.map((a, i) => (
        <section id={a.id} key={a.id} className="scroll-mt-4">
          <Card
            title={<span>{only ? "" : `${i + 1}. `}{a.name} <span className="ml-2 text-[11px] font-normal text-ink3">{a.kind}</span></span>}
            right={<Link href={a.page} className="text-[12px] text-brand hover:underline whitespace-nowrap">Open the screen</Link>}
          >
            <div className="grid gap-3 md:grid-cols-3 mb-4 text-[12.5px] leading-relaxed">
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-ink3 mb-1">Problem it solves</div>
                <p className="text-ink">{a.problem}</p>
              </div>
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-ink3 mb-1">Evidence</div>
                <p className="text-ink2">{a.evidence}</p>
              </div>
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-ink3 mb-1">What it does for the money</div>
                <p className="text-ink2">{a.money}</p>
                <p className="text-ink3 mt-2">User: {a.user}</p>
                <p className="text-ink3 font-mono text-[11px]">{a.file}</p>
              </div>
            </div>
            <AgentFlow agent={a} />
          </Card>
        </section>
      ))}
    </div>
  );
}
