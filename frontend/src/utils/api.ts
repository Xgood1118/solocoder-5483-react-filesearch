import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/',
  timeout: 30_000,
})

export const API = {
  health: () => api.get('/api/health'),

  search: (params: {
    q: string
    path_prefix?: string
    mime?: string
    from_date?: string | number
    to_date?: string | number
    page?: number
    page_size?: number
    cursor?: string
  }) => api.get('/api/search', { params }),

  fileDetail: (fileId: string) => api.get(`/api/files/${fileId}`),

  fileRelated: (fileId: string, per = 5) =>
    api.get(`/api/files/${fileId}/related`, { params: { per } }),

  fileContent: (fileId: string) => `/api/files/${fileId}/content`,

  topTerms: (k = 20) => api.get('/api/stats/top-terms', { params: { k } }),

  topFiles: (k = 20) => api.get('/api/stats/top-files', { params: { k } }),

  qps: () => api.get('/api/stats/qps'),

  indexStatus: () => api.get('/api/index/status'),

  indexRebuild: () => api.post('/api/index/rebuild'),
}
