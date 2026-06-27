import api from './client'

export interface TaxonomyCandidate {
  name: string
  category: string
  aliases: string[]
  support_count: number
  confidence_avg: number
  source_job_ids: string[]
  evidence_samples: string[]
  first_seen_at?: string
  last_seen_at?: string
  status?: string
}

export interface PromotedLabel {
  name: string
  category: string
  aliases: string[]
  support_count: number
  confidence_avg: number
  promoted_at: string
  promoted_by: string
  company_count?: number
}

export interface AliasRecord {
  alias: string
  canonical: string
  category: string
  evidence: string
  added_at: string
}

export interface RejectionRecord {
  name: string
  category: string
  reason: string
  rejected_at: string
}

export interface TaxonomyOverview {
  candidates: TaxonomyCandidate[]
  promoted: PromotedLabel[]
  aliases: AliasRecord[]
  rejections: RejectionRecord[]
  counts: { candidates: number; promoted: number; aliases: number; rejections: number }
}

export const taxonomyApi = {
  overview: () => api.get<TaxonomyOverview>('/taxonomy/candidates').then(r => r.data),
  confirm: (name: string) => api.post('/taxonomy/confirm', { name }).then(r => r.data),
  reject: (name: string, reason = '') => api.post('/taxonomy/reject', { name, reason }).then(r => r.data),
  mergeAlias: (alias: string, canonical: string, category = '') =>
    api.post('/taxonomy/merge-alias', { alias, canonical, category }).then(r => r.data),
  autoPromote: (dryRun = false) => api.post('/taxonomy/auto-promote', { dry_run: dryRun }).then(r => r.data),
}
