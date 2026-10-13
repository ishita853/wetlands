import { cn } from "@/lib/utils";

/**
 * Shared page container: consistent max width and responsive gutters used
 * by the header, footer, and every page section across the site.
 */
export function PageContainer({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page-container"
      className={cn("mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8", className)}
      {...props}
    />
  );
}
