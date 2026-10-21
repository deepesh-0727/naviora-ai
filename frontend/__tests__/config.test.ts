describe('API URL configuration', () => {
  it('uses the production API and secure WebSocket URLs for the release app', () => {
    const { CONFIG } = require('../config');

    expect(CONFIG.API_BASE_URL).toBe('https://naviora-backend-s6je.onrender.com/api/v1');
    expect(CONFIG.WS_BASE_URL).toBe('wss://naviora-backend-s6je.onrender.com/api/v1/stream');
    expect(CONFIG.ENVIRONMENT).toBe('production');
  });
});
