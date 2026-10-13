import { wetlandSlides } from "@/config/wetland-slides";
import { getRamsarSite } from "@/lib/data/ramsar";

export type ResolvedSlide = {
  id: string;
  image: string;
  alt: string;
  title: string;
  subtitle: string | null;
  /** State/UT of the Ramsar Site, shown beside its name. */
  state: string | null;
  /** Site profile link, for slides tied to a Ramsar Site. */
  href: string | null;
  credit: string | null;
  enhanced: boolean;
  fit: "cover" | "contain";
};

/** Joins carousel slides with verified Ramsar Site names and designation years. */
export function getCarouselSlides(): ResolvedSlide[] {
  return wetlandSlides.map((slide) => {
    const site = slide.ramsarId !== null ? getRamsarSite(slide.ramsarId) : undefined;
    if (slide.ramsarId !== null && !site) {
      throw new Error(
        `Carousel slide "${slide.id}" references unknown Ramsar Site ${slide.ramsarId}`,
      );
    }

    let title = "Wetlands of India";
    let subtitle: string | null = null;
    if (site) {
      title = site.name;
      subtitle = `Ramsar Site, Year of Designation: ${site.designationYear}`;
    } else if (slide.kind === "fauna" && slide.species) {
      title = slide.species;
      subtitle = "Wetland birds of India";
    }

    return {
      id: slide.id,
      image: slide.image,
      alt: slide.alt,
      title,
      subtitle,
      state: site?.state ?? null,
      href: site ? `/wetlands/${site.id}` : null,
      credit: slide.credit,
      enhanced: slide.enhanced,
      fit: slide.fit ?? "cover",
    };
  });
}
