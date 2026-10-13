import fs from "node:fs";
import path from "node:path";

import { wetlandSlides } from "@/config/wetland-slides";

export type SiteImage = { src: string; alt: string; credit: string | null };

const IMAGE_EXT = /\.(jpe?g|png|webp|avif)$/i;
const SITES_DIR = path.join(process.cwd(), "public", "images", "sites");

function readCredits(dir: string): Record<string, string> {
  try {
    return JSON.parse(fs.readFileSync(path.join(dir, "credits.json"), "utf8"));
  } catch {
    return {};
  }
}

/**
 * Photographs for one Ramsar Site: files in public/images/sites/<id>/ (see the
 * README there), followed by any homepage carousel image tied to the site.
 * Read at build time; pages are statically generated.
 */
export function getSiteImages(id: number, siteName: string): SiteImage[] {
  const dir = path.join(SITES_DIR, String(id));
  let files: string[] = [];
  try {
    files = fs
      .readdirSync(dir)
      .filter((f) => IMAGE_EXT.test(f))
      .sort();
  } catch {
    // No folder yet for this site.
  }
  const credits = readCredits(dir);
  const images: SiteImage[] = files.map((file, i) => ({
    src: `/images/sites/${id}/${encodeURIComponent(file)}`,
    alt: `${siteName}, photograph ${i + 1}`,
    credit: credits[file] ?? null,
  }));

  for (const slide of wetlandSlides) {
    if (slide.ramsarId === id) {
      images.push({ src: slide.image, alt: slide.alt, credit: slide.credit });
    }
  }
  return images;
}
