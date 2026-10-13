export type DatasetFormat = "CSV" | "GEOJSON" | "GEOTIFF" | "NETCDF" | "SHAPEFILE_ZIP";
export type DatasetStatus = "UPLOADED" | "VALIDATING" | "PROCESSING" | "PUBLISHED" | "FAILED";

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  format: DatasetFormat;
  status: DatasetStatus;
}
