import type { DatasetStatus } from "@/lib/api/admin-types";
import { cn } from "@/lib/utils";

const LABELS: Record<DatasetStatus, string> = {
  UPLOADED: "Uploaded",
  VALIDATING: "Validating",
  PROCESSING: "Processing",
  FAILED: "Failed validation",
  VALIDATED: "Valid · not published",
  PUBLISHED: "Published",
  SUPERSEDED: "Superseded",
};

/** Text label always carries the status; colour only reinforces it. */
export function StatusBadge({ status }: { status: DatasetStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-semibold whitespace-nowrap",
        status === "PUBLISHED" && "border-sedge/60 bg-accent text-accent-foreground",
        status === "FAILED" && "border-destructive/40 bg-destructive/5 text-destructive",
        status === "VALIDATED" && "border-primary/30 bg-card text-primary",
        (status === "SUPERSEDED" ||
          status === "UPLOADED" ||
          status === "VALIDATING" ||
          status === "PROCESSING") &&
          "border-border bg-muted text-muted-foreground",
      )}
    >
      {LABELS[status]}
    </span>
  );
}
