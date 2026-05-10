import { cn } from "@/lib/utils";

interface BookingTimelineProps {
  currentStatus: string;
}

const STEPS = ["pending", "confirmed", "active", "completed"];

const STEP_LABELS: Record<string, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  active: "Active",
  completed: "Completed",
};

const CANCELLED_STATUSES = ["cancelled", "rejected", "no_show"];

export function BookingTimeline({ currentStatus }: BookingTimelineProps) {
  if (CANCELLED_STATUSES.includes(currentStatus)) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3">
        <div className="h-3 w-3 rounded-full bg-destructive" />
        <span className="text-sm font-medium capitalize text-destructive">
          {currentStatus.replace(/_/g, " ")}
        </span>
      </div>
    );
  }

  const currentIndex = STEPS.indexOf(currentStatus);

  return (
    <div className="flex items-center">
      {STEPS.map((step, i) => {
        const isPast = i < currentIndex;
        const isCurrent = i === currentIndex;
        const isFuture = i > currentIndex;

        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold",
                  isPast && "border-primary bg-primary text-primary-foreground",
                  isCurrent && "border-primary bg-primary/10 text-primary",
                  isFuture && "border-muted-foreground/30 bg-muted text-muted-foreground/50"
                )}
              >
                {i + 1}
              </div>
              <span
                className={cn(
                  "text-xs",
                  isCurrent ? "font-medium text-foreground" : "text-muted-foreground"
                )}
              >
                {STEP_LABELS[step]}
              </span>
            </div>

            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  "mx-1 h-0.5 w-8 sm:w-12",
                  i < currentIndex ? "bg-primary" : "bg-muted-foreground/20"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
