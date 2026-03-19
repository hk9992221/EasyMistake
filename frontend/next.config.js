/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost'], // 添加你的图片域名
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // Disable static generation for dynamic routes
  output: 'standalone',
  experimental: {
    // Force dynamic rendering
    forceSwcTransforms: true,
  },
  async rewrites() {
    const internalApiOrigin = process.env.INTERNAL_API_ORIGIN || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${internalApiOrigin}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
