import { describe, it, expect } from 'vitest'
import api from './client'

describe('API Client', () => {
  it('creates axios instance with correct baseURL', () => {
    expect(api.defaults.baseURL).toBe('/api')
  })

  it('has JSON content-type header', () => {
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('has reasonable timeout', () => {
    expect(api.defaults.timeout).toBe(15000)
  })
})
