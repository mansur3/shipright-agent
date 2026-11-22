import { Code2, GitBranch, LogIn, Sparkles, Upload, User, Wrench, Check, type LucideIcon } from "lucide-react";
import { KIND_STYLE, type Agent, type FlowNode, type NodeKind } from "@/lib/agents";

const ICON: Record<NodeKind, LucideIcon> = { input: LogIn, code: Code2, model: Sparkles, tool: Wrench, branch: GitBranch, person: User, output: Upload };

const NODE_W = 176;
const COL_W = 232;
const ROW_H = 96;
const PAD_X = 20;
const PAD_Y = 30;

function nodeHeight(n: FlowNode): number {
  return 38 + (n.rows?.length ?? 0) * 25 + (n.chip ? 30 : 0) + 8;
}

/** Workflow drawn in the style of a node-based builder: cards on a canvas, joined by curves. */
export default function AgentFlow({ agent }: { agent: Agent }) {
  const byId = new Map(agent.nodes.map((n) => [n.id, n]));
  const geo = new Map(
    agent.nodes.map((n) => {
      const h = nodeHeight(n);
      const cy = PAD_Y + n.row * ROW_H + 52;
      return [n.id, { x: PAD_X + n.col * COL_W, y: cy - h / 2, h }] as const;
    })
  );
  const maxCol = Math.max(...agent.nodes.map((n) => n.col));
  const width = PAD_X * 2 + maxCol * COL_W + NODE_W;
  const bottom = Math.max(...agent.nodes.map((n) => geo.get(n.id)!.y + geo.get(n.id)!.h));
  const loopDepth = Math.max(0, ...agent.edges.map((e) => (e.loop ? (typeof e.loop === "number" ? e.loop : 40) : 0)));
  const height = bottom + PAD_Y + (loopDepth ? loopDepth + 14 : 0);

  return (
    <div className="overflow-x-auto rounded-lg border border-[#e3e8ef] bg-[#f4f6f9]" style={{ colorScheme: "light" }}>
      <div className="relative" style={{ width, height, minWidth: width }}>
        <svg className="absolute inset-0 pointer-events-none" width={width} height={height}>
          <defs>
            <marker id={`arr-${agent.id}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0 L8 4 L0 8 z" fill="#94a3b8" />
            </marker>
          </defs>
          {agent.edges.map((e, i) => {
            const a = geo.get(e.from)!;
            const b = geo.get(e.to)!;
            let d: string;
            let lx: number;
            let ly: number;
            if (e.loop) {
              const x1 = a.x + NODE_W / 2;
              const y1 = a.y + a.h;
              const x2 = b.x + NODE_W / 2;
              const y2 = b.y + b.h;
              const dip = Math.max(y1, y2) + (typeof e.loop === "number" ? e.loop : 40);
              d = `M${x1} ${y1} C${x1} ${dip}, ${x2} ${dip}, ${x2} ${y2 + 2}`;
              lx = (x1 + x2) / 2;
              ly = dip - 8;
            } else {
              const x1 = a.x + NODE_W;
              const y1 = a.y + a.h / 2;
              const x2 = b.x;
              const y2 = b.y + b.h / 2;
              const mx = (x1 + x2) / 2;
              d = `M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2 - 2} ${y2}`;
              lx = mx;
              ly = (y1 + y2) / 2;
            }
            return (
              <g key={i}>
                <path d={d} fill="none" stroke="#b4bfcd" strokeWidth={1.6} markerEnd={`url(#arr-${agent.id})`} />
                {e.label && (
                  <g>
                    <rect x={lx - e.label.length * 3.1 - 6} y={ly - 9} width={e.label.length * 6.2 + 12} height={17} rx={8} fill="#f4f6f9" stroke="#dbe2ec" />
                    <text x={lx} y={ly + 3.5} textAnchor="middle" fontSize={10} fill="#64748b">{e.label}</text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>

        {agent.nodes.map((n) => {
          const g = geo.get(n.id)!;
          const st = KIND_STYLE[n.kind];
          const Icon = ICON[n.kind];
          return (
            <div
              key={n.id}
              className="absolute bg-white rounded-xl shadow-sm"
              style={{ left: g.x, top: g.y, width: NODE_W, minHeight: g.h, border: `1.5px solid ${st.border}`, padding: "8px 10px" }}
              title={`${st.label}: ${n.title}`}
            >
              <div className="flex items-center gap-2">
                <span className="w-[22px] h-[22px] rounded-md grid place-items-center shrink-0 text-white" style={{ background: st.bg }}>
                  <Icon size={13} />
                </span>
                <span className="text-[11px] font-bold tracking-wide text-[#1f2937] uppercase leading-tight flex-1">{n.title}</span>
                <span className="w-4 h-4 rounded-full grid place-items-center bg-[#10b981] text-white shrink-0"><Check size={10} strokeWidth={3} /></span>
              </div>
              {n.chip && (
                <div className="mt-2 flex items-center gap-1.5 rounded-md bg-[#f1f4f8] px-2 py-1 text-[11px] text-[#334155]">
                  <Sparkles size={11} style={{ color: st.color }} />
                  <span className="font-semibold">{n.chip}</span>
                  <span className="text-[9px] px-1 rounded bg-white border border-[#dbe2ec] text-[#64748b]">CHAT</span>
                </div>
              )}
              {n.rows && n.rows.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  {n.rows.map((r, i) => (
                    <div key={i} className="flex items-center justify-between gap-1 rounded-md bg-[#f1f4f8] px-2 py-[3px] text-[10.5px] text-[#475569]">
                      <span className="truncate">{r.label}</span>
                      {r.chip && <span className="text-[9px] px-1 rounded bg-white border border-[#dbe2ec] text-[#64748b] shrink-0">{r.chip}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Legend() {
  return (
    <div className="flex flex-wrap gap-3 text-[11px] text-ink2">
      {(Object.keys(KIND_STYLE) as NodeKind[]).map((k) => {
        const st = KIND_STYLE[k];
        return (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ background: st.bg }} />
            {st.label}
          </span>
        );
      })}
    </div>
  );
}
