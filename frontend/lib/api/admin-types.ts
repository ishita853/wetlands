/** Shapes returned by the backend's /admin endpoints. */

export type DatasetStatus =
  "UPLOADED" | "VALIDATING" | "PROCESSING" | "FAILED" | "VALIDATED" | "PUBLISHED" | "SUPERSEDED";

export type AdminDataset = {
  id: string;
  name: string;
  description: string | null;
  kind: "CLIMATE_INDICATOR";
  theme: string | null;
  format: string;
  status: DatasetStatus;
  original_filename: string;
  size_bytes: number;
  sha256: string;
  validation_errors: string[] | null;
  summary: {
    source: string;
    baseline: string;
    years: [number, number] | null;
    metrics: { key: string; label: string; unit: string }[];
    siteCount: number;
  } | null;
  published_at: string | null;
  created_at: string;
  uploaded_by_username: string | null;
};

export type ClimateThemeStatus = {
  theme: string;
  title: string;
  published: AdminDataset | null;
};
