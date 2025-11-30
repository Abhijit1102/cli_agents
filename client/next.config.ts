import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  productionBrowserSourceMaps: false, // 🔥 Fix sourceMapURL errors
};

export default nextConfig;
