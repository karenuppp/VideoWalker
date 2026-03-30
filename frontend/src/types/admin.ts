export interface AdminCamera {
  id: number
  camera_id: string
  name: string
  rtsp_url: string | null
  enabled: boolean
}

export interface SceneItem {
  id: number
  camera_id: number
  camera_name: string
  scene_key: string
  name: string
  description: string | null
  detect_api: string | null
  enabled: boolean
  frame_interval_seconds: number | null
  model_name?: string | null
  rule?: {
    type?: string
    target?: string
    op?: string
    threshold?: number
  } | null
}
