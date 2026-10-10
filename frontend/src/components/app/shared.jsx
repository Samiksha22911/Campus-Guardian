import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import { useApp, can } from "@/lib/app-store";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import {
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";

/* ---------- StatusBadge ---------- */

const toneClass = {
  success: "bg-success/12 text-success border-success/35",
  warning: "bg-warning/12 text-warning border-warning/35",
  danger: "bg-destructive/15 text-destructive border-destructive/40",
  muted: "bg-muted text-muted-foreground border-border",
  primary: "bg-primary/12 text-primary border-primary/35",
};

export function Badge2({
  tone = "muted",
  children,
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider",
        toneClass[tone]
      )}
    >
      {children}
    </span>
  );
}

export const statusTone = (status) =>
  status === "granted" ||
  status === "resolved" ||
  status === "active" ||
  status === "registered" ||
  status === "match"
    ? "success"
    : status === "denied" ||
      status === "critical" ||
      status === "suspended" ||
      status === "mismatch" ||
      status === "high"
    ? "danger"
    : status === "uncertain" ||
      status === "pending" ||
      status === "unavailable" ||
      status === "open" ||
      status === "medium"
    ? "warning"
    : status === "manual" ||
      status === "acknowledged"
    ? "primary"
    : "muted";

export function StatusBadge({ status }) {
  return (
    <Badge2 tone={statusTone(status)}>
      {status}
    </Badge2>
  );
}

export function FaceBadge({ value }) {
  return (
    <Badge2 tone={statusTone(value)}>
      {value}
    </Badge2>
  );
}

/* ---------- ConfidenceMeter ---------- */

export function ConfidenceMeter({
  value,
  label,
}) {
  const tone =
    value >= 90
      ? "bg-success"
      : value >= 70
      ? "bg-warning"
      : "bg-destructive";

  const safeValue = Math.max(
    0,
    Math.min(100, value)
  );

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full",
            tone
          )}
          style={{
            width: `${safeValue}%`,
          }}
        />
      </div>

      <span className="font-mono text-[0.65rem] tabular-nums text-muted-foreground">
        {label ?? `${value.toFixed(1)}%`}
      </span>
    </div>
  );
}

/* ---------- Sparkline ---------- */

export function Sparkline({
  points,
  tone = "primary",
}) {
  const max = Math.max(...points, 1);

  const denominator =
    points.length - 1 || 1;

  const d = points
    .map(
      (point, index) =>
        `${(index / denominator) * 100},${
          28 - (point / max) * 24
        }`
    )
    .join(" ");

  const stroke =
    tone === "danger"
      ? "var(--destructive)"
      : tone === "warning"
      ? "var(--warning)"
      : tone === "success"
      ? "var(--success)"
      : "var(--primary)";

  return (
    <svg
      viewBox="0 0 100 30"
      preserveAspectRatio="none"
      className="mt-2 h-7 w-full"
    >
      <polyline
        points={d}
        fill="none"
        stroke={stroke}
        strokeWidth="1.6"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/* ---------- StatCard ---------- */

export function StatCard({
  label,
  value,
  spark,
  tone = "primary",
  hint,
}) {
  const bar = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-destructive",
    muted: "bg-muted",
  }[tone];

  return (
    <div className="panel relative overflow-hidden px-4 py-3">
      <span
        className={cn(
          "absolute inset-y-0 left-0 w-[3px]",
          bar
        )}
      />

      <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>

      <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-foreground">
        {value}
      </p>

      {hint ? (
        <p className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}

      {spark ? (
        <Sparkline
          points={spark}
          tone={tone}
        />
      ) : null}
    </div>
  );
}

/* ---------- Panel ---------- */

export function Card({
  title,
  subtitle,
  action,
  children,
  className,
  bodyClassName,
}) {
  return (
    <section
      className={cn(
        "panel flex flex-col overflow-hidden",
        className
      )}
    >
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
        <div>
          <h2 className="font-mono text-[0.68rem] uppercase tracking-[0.18em] text-muted-foreground">
            {title}
          </h2>

          {subtitle ? (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {subtitle}
            </p>
          ) : null}
        </div>

        {action}
      </header>

      <div
        className={cn(
          "min-h-0 flex-1",
          bodyClassName
        )}
      >
        {children}
      </div>
    </section>
  );
}

/* ---------- DataTable ---------- */

export function DataTable({
  rows,
  columns,
  onRowClick,
  searchPlaceholder = "Search…",
  searchFields,
  pageSize = 12,
  toolbar,
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState(null);

  const filtered = useMemo(() => {
    let output = rows;

    /* Search */
    if (query && searchFields) {
      const needle = query.toLowerCase();

      output = output.filter((row) =>
        searchFields(row)
          .toLowerCase()
          .includes(needle)
      );
    }

    /* Sorting */
    if (sort) {
      const column = columns.find(
        (item) => item.key === sort.key
      );

      if (column?.sortValue) {
        output = [...output].sort(
          (a, b) => {
            const aValue =
              column.sortValue(a);

            const bValue =
              column.sortValue(b);

            return aValue > bValue
              ? sort.dir
              : aValue < bValue
              ? -sort.dir
              : 0;
          }
        );
      }
    }

    return output;
  }, [
    rows,
    query,
    sort,
    columns,
    searchFields,
  ]);

  const pages = Math.max(
    1,
    Math.ceil(filtered.length / pageSize)
  );

  const safePage = Math.min(
    page,
    pages - 1
  );

  const startIndex =
    safePage * pageSize;

  const view = filtered.slice(
    startIndex,
    startIndex + pageSize
  );

  const handleSort = (column) => {
    if (!column.sortValue) return;

    setSort((current) => {
      if (current?.key === column.key) {
        return {
          key: column.key,
          dir: current.dir === 1 ? -1 : 1,
        };
      }

      return {
        key: column.key,
        dir: 1,
      };
    });
  };

  return (
    <div className="flex flex-col">

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">

        {searchFields ? (
          <div className="relative min-w-[190px] flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />

            <Input
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(0);
              }}
              placeholder={searchPlaceholder}
              className="h-8 pl-8 font-mono text-xs"
            />
          </div>
        ) : null}

        {toolbar}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">

          <thead>
            <tr className="border-b border-border bg-surface-2/40">

              {columns.map((column) => (
                <th
                  key={column.key}
                  onClick={() =>
                    handleSort(column)
                  }
                  className={cn(
                    "whitespace-nowrap px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.14em] text-muted-foreground",
                    column.sortValue &&
                      "cursor-pointer select-none hover:text-foreground",
                    column.className
                  )}
                >
                  <span className="inline-flex items-center gap-1">

                    {column.header}

                    {sort?.key === column.key ? (
                      sort.dir === 1 ? (
                        <ChevronUp className="size-3" />
                      ) : (
                        <ChevronDown className="size-3" />
                      )
                    ) : null}

                  </span>
                </th>
              ))}

            </tr>
          </thead>

          <tbody>

            {view.map((row) => (
              <tr
                key={row.id}
                onClick={() =>
                  onRowClick?.(row)
                }
                className={cn(
                  "border-b border-border/60 last:border-0",
                  onRowClick &&
                    "cursor-pointer hover:bg-surface-2/60"
                )}
              >

                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      "px-3 py-2 align-middle",
                      column.className
                    )}
                  >
                    {column.render(row)}
                  </td>
                ))}

              </tr>
            ))}

            {view.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-8 text-center text-sm text-muted-foreground"
                >
                  No records match the current filters.
                </td>
              </tr>
            ) : null}

          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-2">

        <span className="font-mono text-[0.65rem] text-muted-foreground">
          {filtered.length} records · page{" "}
          {safePage + 1}/{pages}
        </span>

        <div className="flex gap-1">

          <Button
            variant="outline"
            size="sm"
            disabled={safePage === 0}
            onClick={() =>
              setPage(safePage - 1)
            }
          >
            Prev
          </Button>

          <Button
            variant="outline"
            size="sm"
            disabled={
              safePage >= pages - 1
            }
            onClick={() =>
              setPage(safePage + 1)
            }
          >
            Next
          </Button>

        </div>
      </div>
    </div>
  );
}

/* ---------- DetailDrawer ---------- */

export function DetailDrawer({
  open,
  onOpenChange,
  title,
  children,
}) {
  return (
    <Sheet
      open={open}
      onOpenChange={onOpenChange}
    >
      <SheetContent className="w-full overflow-y-auto border-border bg-surface sm:max-w-lg">

        <SheetHeader>
          <SheetTitle className="font-mono text-sm uppercase tracking-[0.16em] text-muted-foreground">
            {title}
          </SheetTitle>
        </SheetHeader>

        <div className="space-y-5 px-4 pb-8">
          {children}
        </div>

      </SheetContent>
    </Sheet>
  );
}

/* ---------- Field ---------- */

export function Field({
  label,
  children,
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-2 text-sm last:border-0">

      <span className="font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>

      <span className="text-right text-foreground">
        {children}
      </span>

    </div>
  );
}

/* ---------- RoleGate ---------- */

export function RoleGate({
  permission,
  children,
  fallback = null,
}) {
  const { user } = useApp();

  const hasPermission = can(
    user?.role,
    permission
  );

  return hasPermission ? (
    <>{children}</>
  ) : (
    <>{fallback}</>
  );
}

/* ---------- LiveFeedFrame ---------- */

export function LiveFeedFrame({
  src,
  label,
  plate,
  confidence,
  compact,
}) {
  return (
    <figure className="relative overflow-hidden rounded-md border border-border bg-black">

      <img
        src={src}
        alt={`${label} camera feed`}
        className={cn(
          "w-full object-cover opacity-85",
          compact
            ? "aspect-video"
            : "aspect-video"
        )}
      />

      {/* Scanline */}
      <div className="pointer-events-none absolute inset-0 scanline opacity-40" />

      {/* Sweep line */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-8 bg-primary/20 blur-md sweep-line" />

      {/* Vehicle Detection Box */}
      <div className="pointer-events-none absolute left-[46%] top-[52%] h-[34%] w-[38%] -translate-x-1/2 -translate-y-1/2 border-2 border-primary">

        <span className="absolute -top-5 left-0 bg-background/85 px-1 font-mono text-[0.6rem] text-primary">
          VEHICLE
        </span>

      </div>

      {/* Number Plate Detection */}
      {plate ? (
        <div className="pointer-events-none absolute left-[46%] top-[66%] h-[9%] w-[20%] -translate-x-1/2 border-2 border-success">

          <span className="absolute -bottom-5 left-0 whitespace-nowrap bg-background/85 px-1 font-mono text-[0.6rem] text-success">
            {plate}

            {confidence !== undefined
              ? ` · ${confidence.toFixed(1)}%`
              : ""}
          </span>

        </div>
      ) : null}

      {/* Camera Label */}
      <figcaption className="absolute inset-x-0 top-0 flex items-center justify-between p-2">

        <span className="rounded bg-background/75 px-1.5 py-0.5 font-mono text-[0.62rem] backdrop-blur">
          {label}
        </span>

        <span className="flex items-center gap-1.5 rounded bg-background/75 px-1.5 py-0.5 font-mono text-[0.6rem] uppercase text-destructive backdrop-blur">

          <span className="live-dot inline-block size-1.5 rounded-full bg-destructive" />

          live
        </span>

      </figcaption>

    </figure>
  );
}

