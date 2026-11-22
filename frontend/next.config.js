/** @type {import('next').NextConfig} */
// NEXT_EXPORT=1 builds a static site (out/) that the API serves from backend/public, so one app deploys as one unit.
// Without it, `next dev` proxies /api to the backend on localhost:8000.
const exporting = process.env.NEXT_EXPORT === "1";

// API_ORIGIN and NEXT_DIST_DIR let a second dev server (for testing) run beside the main one on :3000 without sharing its build folder.
const apiOrigin = process.env.API_ORIGIN || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  ...(process.env.NEXT_DIST_DIR ? { distDir: process.env.NEXT_DIST_DIR } : {}),
  ...(exporting
    ? { output: "export", trailingSlash: true, images: { unoptimized: true } }
    : {
        async rewrites() {
          return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
        },
      }),
};

module.exports = nextConfig;
