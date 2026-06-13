export interface SearchHit {
  file_id: string
  path: string
  name: string
  size: number
  mtime: number
  mime_type: string
  owner: string
  tags: string[]
  ext: string
  score: number
  bm25_score: number
  snippet_html: string
  snippet_plain: string
  hit_positions: Array<[number, number]>
  ocr_low_conf: boolean
  field_weights?: Record<string, number>
}

export interface SearchParsed {
  free_text: string
  phrases: string[]
  and_terms: string[]
  or_terms: string[]
  not_terms: string[]
  field_filters: Array<[string, string, string]>
  error?: string
}

export interface SearchResponse {
  results: SearchHit[]
  cursor: string | null
  parsed: SearchParsed
  total_returned: number
  total_found_cap?: number
  error?: string
}

export interface FileDetail {
  file_id: string
  path: string
  name: string
  size: number
  mtime: number
  mime_type: string
  owner: string
  tags: string[]
  ext: string
  ocr_low_conf: boolean
  content_preview: string
  parent_dir: string
}

export interface RelatedFiles {
  same_dir: FileMeta[]
  same_tags: FileMeta[]
  same_owner: FileMeta[]
}

export interface FileMeta {
  file_id: string
  path: string
  name: string
  size: number
  mtime: number
  mime_type: string
  owner: string
  tags: string[]
  ext: string
}

export interface TopTerm {
  term: string
  count: number
}

export interface TopFile {
  file_id: string
  label: string
  count: number
}

export interface QpsBucket {
  bucket: string
  count: number
}

export interface QpsSummary {
  per_minute: QpsBucket[]
  total_last_hour: number
  total_last_day: number
  peak_qpm: number
}

export interface IndexStatus {
  total_files_scanned: number
  indexed_count: number
  failed_count: number
  deleted_count: number
  skipped_count: number
  last_update_ts: number
  last_update: string | null
  in_progress: boolean
  recent_failures: Array<{ path: string; error: string; ts: number }>
  index_dir: string
  root_dir: string
}

export interface HistoryItem {
  q: string
  at: number
}
