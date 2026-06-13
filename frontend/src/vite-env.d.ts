declare module '*.css'

interface ImportMetaEnv {
  readonly VITE_PORT?: string
  readonly VITE_API_BASE?: string
  readonly FLASK_PORT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
