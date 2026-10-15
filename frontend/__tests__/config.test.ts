describe('API URL configuration', () => {
  it('builds API and websocket URLs from the configured API host', () => {
    const { buildServiceUrls } = require('../config');
    const urls = buildServiceUrls('https://api.naviora.ai');

    expect(urls.API_BASE_URL).toBe('https://api.naviora.ai/api/v1');
    expect(urls.WS_BASE_URL).toBe('wss://api.naviora.ai/api/v1/stream');
  });
});
