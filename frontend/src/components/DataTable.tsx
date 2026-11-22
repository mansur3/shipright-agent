import clsx from "clsx";
import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  maxHeight?: number;
  empty?: ReactNode;
  rowKey?: (row: T, index: number) => string | number;
}

/**
 * Scrollable data table with sticky headers, horizontal + vertical overflow,
 * and a max height. Mirrors the `.table-wrap` / `.data-table` pattern from the
 * platform's base CSS so tall tables scroll independently of the page.
 */
export default function DataTable<T extends object>({
  columns,
  data,
  maxHeight = 520,
  empty = "No data",
  rowKey,
}: DataTableProps<T>) {
  return (
    <div
      className="dt-scroll rounded-b-[10px] border border-t-0 border-line"
      style={{ maxHeight }}
    >
      <table className="dt-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.className}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="text-ink3 py-6 text-center"
                style={{ whiteSpace: "normal" }}
              >
                {empty}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr key={rowKey ? rowKey(row, i) : i}>
                {columns.map((c) => (
                  <td key={c.key} className={c.className}>
                    {c.render ? c.render(row) : ((row as Record<string, unknown>)[c.key] as ReactNode) ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Th({ children, className }: { children: ReactNode; className?: string }) {
  return <th className={clsx("text-ink2 font-medium", className)}>{children}</th>;
}
