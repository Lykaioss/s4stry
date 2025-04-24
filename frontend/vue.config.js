const HtmlWebpackPlugin = require('html-webpack-plugin')

module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        pathRewrite: { '^/api': '' },
      },
      '/blockchain': {
        target: 'http://localhost:7575',
        changeOrigin: true,
        pathRewrite: { '^/blockchain': '' },
      },
    },
  },
  configureWebpack: {
    plugins: [
      new HtmlWebpackPlugin({
        template: './public/index.html',
        filename: 'index.html',
        inject: true,
        templateParameters: {
          BASE_URL: process.env.NODE_ENV === 'production' ? '/' : '/',
        },
      }),
    ],
  },
  chainWebpack: (config) => {
    // Remove the default HtmlWebpackPlugin instance
    config.plugins.delete('html');
    // Adjust CopyPlugin to exclude index.html
    config.plugin('copy').tap(([options]) => {
      options.patterns = options.patterns.filter(
        (pattern) => !pattern.from.includes('index.html')
      );
      return [options];
    });
  },
}