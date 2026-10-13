import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      // Dataset uploads (backend MAX_UPLOAD_MB = 25) plus multipart overhead.
      bodySizeLimit: "26mb",
    },
  },
};

export default nextConfig;
