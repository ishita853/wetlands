/**
 * Homepage carousel images (project-supplied, in /public/images).
 *
 * Site slides reference a Ramsar Site by its official site number
 * (`ramsarId`); the displayed name and year of designation are read from the
 * Ramsar Sites Information Service dataset (data/ramsar-sites.json), never
 * typed here. Slides whose site has not been identified keep `ramsarId: null`
 * and show a neutral "Wetlands of India" title.
 *
 * `enhanced: true` marks images regenerated/upscaled with an AI image tool
 * from the original photographs (originals kept in images/wetlands/originals).
 */
export type WetlandSlide = {
  id: string;
  image: string;
  /** Describes what the image shows (not a claim about the site). */
  alt: string;
  kind: "site" | "fauna";
  /** Official Ramsar Site number (kind "site"), if identified. */
  ramsarId: number | null;
  /** Species name (kind "fauna"). */
  species?: string;
  /** Credit as printed on the supplied photograph, if any. */
  credit: string | null;
  enhanced: boolean;
  /**
   * Low-resolution and portrait images are shown whole on a dark field
   * instead of being cropped and upscaled across the full width.
   */
  fit?: "cover" | "contain";
};

export const wetlandSlides: WetlandSlide[] = [
  {
    id: "sundarban",
    image: "/images/wetlands/sundarban.png",
    alt: "A mangrove-fringed mudflat curving into calm estuarine water under a blue sky.",
    kind: "site",
    ramsarId: 2370, // Sundarban Wetland
    credit: null,
    enhanced: true,
  },
  {
    id: "lonar",
    image: "/images/wetlands/lonar.png",
    alt: "A near-circular lake inside a forested crater basin, seen from the rim.",
    kind: "site",
    ramsarId: 2441, // Lonar Lake
    credit: null,
    enhanced: true,
  },
  {
    id: "zachhua-2018",
    image: "/images/wetlands/zachhua-2018-04-10.png",
    alt: "A wetland channel through floating vegetation, with a boat and forested hills beyond.",
    kind: "site",
    ramsarId: null,
    credit: "E&F, MADC · N. Zachhua",
    enhanced: true,
  },
  {
    id: "siliserh-lake",
    image: "/images/wetlands/siliserh-lake.png",
    alt: "A lake reflecting forested hills and a palace building on the shore.",
    kind: "site",
    ramsarId: 2581, // Siliserh lake
    credit: null,
    enhanced: true,
  },
  {
    id: "sunset-wetland",
    image: "/images/wetlands/sunset-wetland.png",
    alt: "Waterbirds on a shallow wetland at sunset, framed by trees.",
    kind: "site",
    ramsarId: null,
    credit: null,
    enhanced: true,
  },
  {
    id: "nangal",
    image: "/images/wetlands/nangal.png",
    alt: "Clear blue-green water along a bank of mixed deciduous trees.",
    kind: "site",
    ramsarId: 2407, // Nangal Wildlife Sanctuary
    credit: null,
    enhanced: true,
  },
  {
    id: "zachhua-2021",
    image: "/images/wetlands/zachhua-2021-06-18.png",
    alt: "A forest-ringed lake and marsh under low monsoon cloud in hill country.",
    kind: "site",
    ramsarId: null,
    credit: "E&F, MADC · N. Zachhua",
    enhanced: true,
  },
  {
    id: "river-sandbar",
    image: "/images/wetlands/river-sandbar.png",
    alt: "Birds resting on a sandbar in a river flanked by forested hills.",
    kind: "site",
    ramsarId: null,
    credit: null,
    enhanced: true,
  },
  {
    id: "bar-headed-geese-flock",
    image: "/images/fauna/bar-headed-geese-flock.png",
    alt: "Bar-headed geese and a greylag goose swimming in a shallow river.",
    kind: "fauna",
    ramsarId: null,
    species: "Bar-headed geese",
    credit: null,
    enhanced: true,
  },
  {
    id: "bar-headed-geese-pair",
    image: "/images/fauna/bar-headed-geese-pair.png",
    alt: "Two bar-headed geese swimming side by side.",
    kind: "fauna",
    ramsarId: null,
    species: "Bar-headed geese",
    credit: null,
    enhanced: true,
  },
];
