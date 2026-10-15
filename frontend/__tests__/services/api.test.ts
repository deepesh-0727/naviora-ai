import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiService } from '../../src/services/api';

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
}));

const mockedStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;
const originalFetch = global.fetch;

describe('apiService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedStorage.getItem.mockImplementation(async key => key === 'access_token' ? 'test-token' : 'hi-IN');
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it('attaches the stored bearer token and language to a request', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 17, status: 'scheduled' }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await apiService.get<{ id: number; status: string }>('/appointments');

    expect(result).toEqual({ data: { id: 17, status: 'scheduled' }, status: 200 });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/appointments$/),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer test-token', 'Accept-Language': 'hi-IN' }),
      }),
    );
  });

  it('returns the server response body on an unauthorized response', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Session expired' }),
    }) as unknown as typeof fetch;

    await expect(apiService.get('/profile')).resolves.toEqual({ error: 'Session expired', status: 401 });
  });

  it('includes field locations in validation errors', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ details: [{ loc: ['body', 'phone'], msg: 'invalid number' }] }),
    }) as unknown as typeof fetch;

    await expect(apiService.post('/auth/login', {})).resolves.toEqual({
      error: 'phone: invalid number',
      status: 422,
    });
  });

  it('returns a network error result when fetch rejects', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('offline')) as unknown as typeof fetch;

    await expect(apiService.get('/profile')).resolves.toEqual({ error: 'offline', status: 0 });
  });
});
