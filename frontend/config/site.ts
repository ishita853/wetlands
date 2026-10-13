export const siteConfig = {
  name: "Indian Wetlands Climate & Environment Monitoring Portal",
  shortName: "Indian Ramsar Wetlands",
  tagline: "Climate & Environment Monitoring Portal",
  description:
    "Monitoring portal for India's Ramsar wetlands: spatial wetland information, climate indicators (wetland drought, precipitation extremes, heat waves, cold waves), water quality, and datasets.",
};

export interface NavLink {
  title: string;
  href: string;
}

export interface NavGroup {
  title: string;
  href: string;
  items: NavLink[];
}

export type NavEntry = NavLink | NavGroup;

export function isNavGroup(entry: NavEntry): entry is NavGroup {
  return "items" in entry;
}

export const climateThemes: NavLink[] = [
  { title: "Wetland Drought", href: "/climate/drought" },
  { title: "Precipitation Extremes", href: "/climate/precipitation" },
  { title: "Heat Waves", href: "/climate/heat-waves" },
  { title: "Cold Waves", href: "/climate/cold-waves" },
];

export const mainNav: NavEntry[] = [
  { title: "Home", href: "/" },
  { title: "About", href: "/about" },
  { title: "Ramsar Wetlands", href: "/wetlands" },
  { title: "Climate Monitoring", href: "/climate", items: climateThemes },
  { title: "Water Quality", href: "/water-quality" },
  { title: "Analysis", href: "/analysis" },
  { title: "Datasets", href: "/datasets" },
];

export const adminNav: NavLink = { title: "Admin Login", href: "/admin/login" };

/** Authoritative external references. Linked, never scraped. */
export const referenceSources = {
  ramsarIndia: {
    title: "Ramsar Convention — India country profile",
    href: "https://www.ramsar.org/country-profile/india",
  },
  wetlandsOfIndia: {
    title: "Wetlands of India Portal",
    href: "https://indianwetlands.in/",
  },
} as const;

/** Credit line for all Ramsar Site data shown on the portal. */
export const ramsarCredit = {
  text: "Ramsar Convention on Wetlands",
  href: referenceSources.ramsarIndia.href,
} as const;
