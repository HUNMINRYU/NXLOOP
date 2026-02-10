/** @type {import('next').NextConfig} */
const nextConfig = {
  // Cloud Run에서는 build 결과를 dist로 두고 실행한다.
  distDir: process.env.NEXLOOP_NEXT_DIST_DIR || "dist",
  images: {
    unoptimized: true,
  },
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        ignored: ["**/node_modules", "**/dist", "**/.git"],
      };
    }
    return config;
  },
};

module.exports = nextConfig;

