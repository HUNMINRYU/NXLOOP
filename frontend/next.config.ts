import type { NextConfig } from 'next';

const distDir = process.env.NEXLOOP_NEXT_DIST_DIR || 'dist';

const nextConfig: NextConfig = {
    distDir,
    images: {
        unoptimized: true,
    },
    webpack: (config, { dev }) => {
        if (dev) {
            config.watchOptions = {
                ignored: ['**/node_modules', '**/dist', '**/.git'],
            };
        }
        return config;
    },
};

export default nextConfig;
