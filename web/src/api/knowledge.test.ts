import { describe, it, expect } from 'vitest'
import { knowledgeApi } from './knowledge'

describe('knowledgeApi', () => {
  it('exports all expected methods', () => {
    expect(typeof knowledgeApi.search).toBe('function')
    expect(typeof knowledgeApi.skillFrequency).toBe('function')
    expect(typeof knowledgeApi.versions).toBe('function')
    expect(typeof knowledgeApi.semanticSearch).toBe('function')
    expect(typeof knowledgeApi.vectorStatus).toBe('function')
    expect(typeof knowledgeApi.vectorRebuild).toBe('function')
    expect(typeof knowledgeApi.vectorClear).toBe('function')
  })
})
