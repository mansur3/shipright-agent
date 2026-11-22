import clsx from "clsx";
import type { ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export default function Card({
  title,
  right,
  children,
  className,
  bodyClassName,
}: CardProps) {
  return (
    <section
      className={clsx("bg-panel border border-line rounded-[10px]", className)}
    >
      {title !== undefined && (
        <header className="px-[18px] py-3 text-[13px] font-semibold border-b border-line rounded-t-[10px] flex items-center justify-between gap-3">
          <span className="truncate">{title}</span>
          {right}
        </header>
      )}
      <div className={clsx("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}
