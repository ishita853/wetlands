import { ImageIcon } from "lucide-react";
import Image from "next/image";

import type { SiteImage } from "@/lib/data/site-images";
import { cn } from "@/lib/utils";

/** Photo grid for a site profile: the first photograph leads at double size. */
export function SiteGallery({ images, siteName }: { images: SiteImage[]; siteName: string }) {
  if (images.length === 0) {
    return (
      <div className="flex min-h-40 flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-card/60 p-6 text-center text-sm text-muted-foreground">
        <ImageIcon className="size-6" aria-hidden="true" />
        Photographs of {siteName} will be added soon.
      </div>
    );
  }

  return (
    <ul
      aria-label={`Photographs of ${siteName}`}
      className="grid auto-rows-36 grid-cols-2 gap-3 sm:auto-rows-44 sm:grid-cols-3"
    >
      {images.map((image, i) => (
        <li
          key={image.src}
          className={cn(
            "group relative overflow-hidden rounded-md bg-muted shadow-sm",
            i === 0 && images.length > 1 && "col-span-2 row-span-2",
            images.length === 1 && "col-span-2 row-span-2 sm:col-span-3",
          )}
        >
          <figure className="size-full">
            <Image
              src={image.src}
              alt={image.alt}
              fill
              sizes={i === 0 ? "(min-width: 640px) 32rem, 100vw" : "16rem"}
              className="object-cover transition-transform duration-500 group-hover:scale-[1.03] motion-reduce:transition-none"
            />
            {image.credit ? (
              <figcaption className="absolute inset-x-0 bottom-0 truncate bg-linear-to-t from-black/60 to-transparent px-2.5 pt-4 pb-1.5 text-[11px] text-white">
                {image.credit.startsWith("Photo") ? image.credit : `Photo: ${image.credit}`}
              </figcaption>
            ) : null}
          </figure>
        </li>
      ))}
    </ul>
  );
}
