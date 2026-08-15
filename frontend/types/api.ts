export interface EnvironmentChecks {
  gemini_api_key_configured: boolean
  database_url_configured: boolean
}

export interface HealthCheckResponse {
  status: string
  project: string
  version: string
  timestamp: string
  environment_checks: EnvironmentChecks
}

export type RoadmapPhaseStatus = 'active' | 'pending' | 'completed'

export interface RoadmapPhase {
  id: number
  name: string
  desc: string
  status: RoadmapPhaseStatus
}
