// MapLibre GL 6 loads its web worker from a file beside its own module
// (import.meta.url). Once bundled, that file is not emitted, so the worker
// fails silently and maps never load. Serve the worker (and the shared chunk
// it imports) from public/ instead; components/maps/ramsar-map.tsx points
// MapLibre at it with setWorkerUrl(). Runs before `dev` and `build`.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "node_modules", "maplibre-gl", "dist");
const dest = join(root, "public", "vendor", "maplibre");

mkdirSync(dest, { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(join(src, file), join(dest, file));
}
console.log("Copied MapLibre worker to public/vendor/maplibre");
