/** @type {import('next').NextConfig} */
const nextConfig = {
  // Cloud Run에서는 build 결과를 dist로 두고 실행한다.
  distDir: process.env.NEXLOOP_NEXT_DIST_DIR || "dist",
  async rewrites() {
    const backendBaseUrl =
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "https://nexloop-backend-ekhgbjmhqq-du.a.run.app";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendBaseUrl}/api/v1/:path*`,
      },
    ];
  },
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
