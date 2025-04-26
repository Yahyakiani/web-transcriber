// frontend/web-transcriber/next.config.ts
import path from 'path';
import type { NextConfig } from 'next';
import type { Configuration as WebpackConfiguration } from 'webpack';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',

  webpack: (
    config: WebpackConfiguration,
  ): WebpackConfiguration => {

    // Ensure resolve object exists
    config.resolve = config.resolve || {};

    // --- Modified Alias Handling ---
    // Initialize alias as an empty object if it's null or undefined
    config.resolve.alias = config.resolve.alias || {};

    // Check if it's an object (it might be an array or null/undefined initially)
    // We assume we want to add to it as if it's an object map.
    // Use a type assertion to tell TS we know it's an indexable object here.
    if (config.resolve.alias && typeof config.resolve.alias === 'object') {
         (config.resolve.alias as { [key: string]: string | string[] | false })['@'] = path.resolve(__dirname, 'src');
    } else {
        // Handle the case where alias might have been initialized as an array?
        // For simplicity, we'll assume it should be an object map for path aliases.
        // If it wasn't an object, we initialize it as one.
         config.resolve.alias = {
            '@': path.resolve(__dirname, 'src')
         };
    }
    // --- End Modified Alias Handling ---

    return config;
  },
};

export default nextConfig;