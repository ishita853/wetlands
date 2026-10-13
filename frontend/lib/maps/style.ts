/**
 * MapLibre GL JS base style configuration.
 *
 * The style URL is deliberately not hardcoded here — it will be sourced
 * from an environment variable once a basemap provider is chosen in a
 * future step.
 */
export const DEFAULT_MAP_STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "";
