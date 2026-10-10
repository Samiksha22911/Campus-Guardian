import { cn } from "@/lib/utils";

/* ---------- Panel ---------- */

export function Panel({
  title,
  subtitle,
  action,
  children,
  className,
}) {
  return (
    <section
      className={cn(
        "panel flex flex-col overflow-hidden",
        className
      )}
    >
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2 className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground">
            {title}
          </h2>

          {subtitle ? (
            <p className="mt-0.5 text-sm font-medium text-foreground">
              {subtitle}
            </p>
          ) : null}
        </div>

        {action}
      </header>

      <div className="min-h-0 flex-1">
        {children}
      </div>
    </section>
  );
}

/* ---------- Tag ---------- */

export function Tag({
  tone = "muted",
  children,
}) {
  const tones = {
    muted:
      "bg-muted text-muted-foreground border-border",

    primary:
      "bg-primary/12 text-primary border-primary/30",

    success:
      "bg-success/12 text-success border-success/30",

    warning:
      "bg-warning/12 text-warning border-warning/30",

    danger:
      "bg-destructive/15 text-destructive border-destructive/35",

    accent:
      "bg-accent/12 text-accent border-accent/30",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider",
        tones[tone]
      )}
    >
      {children}
    </span>
  );
}

/* ---------- Stat ---------- */

export function Stat({
  label,
  value,
  delta,
  tone = "primary",
}) {
  const bar = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-destructive",
  };

  return (
    <div className="panel relative overflow-hidden px-4 py-3.5">
      <span
        className={cn(
          "absolute inset-y-0 left-0 w-[3px]",
          bar[tone]
        )}
      />

      <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>

      <p className="mt-1.5 font-mono text-2xl font-semibold tabular-nums text-foreground">
        {value}
      </p>

      {delta ? (
        <p className="mt-0.5 text-xs text-muted-foreground">
          {delta}
        </p>
      ) : null}
    </div>
  );
}

/* ---------- Meter ---------- */

export function Meter({
  value,
  tone,
}) {
  const bar = {
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-destructive",
  };

  return (
    <div className="h-1 w-14 overflow-hidden rounded-full bg-muted">
      <div
        className={cn(
          "h-full rounded-full",
          bar[tone]
        )}
        style={{
          width: `${value}%`,
        }}
      />
    </div>
  );
}

