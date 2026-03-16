export interface Alert {
  id: number
  camera_id: number
  alert_type: string
  scene_name?: string | null
  confidence: number | null
  description: string | null
  image_path: string
  status: 'unread' | 'read' | 'resolved'
  detected_at: string
  created_at: string
  camera?: Camera
  details?: Record<string, any>
}

export interface Camera {
  id: number
  camera_id: string
  name: string
  cms_url: string
  location: string | null
  status: string
  last_frame_time: string | null
  scenes?: string[]
}

export interface AlertStats {
  total: number
  unread: number
  read: number
  resolved: number
  by_type: Record<string, number>
}

export interface SceneConfig {
  type: string
  name: string
  name_en: string
  description: string
  color: string
  icon: string
}
