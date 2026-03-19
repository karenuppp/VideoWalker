import axios from 'axios'
import type { AdminCamera, SceneItem } from '../types/admin'

const API_BASE_URL = '/api/v1/admin'

export const adminApi = {
  async listCameras(): Promise<AdminCamera[]> {
    const response = await axios.get<AdminCamera[]>(`${API_BASE_URL}/cameras`)
    return response.data
  },

  async createCamera(payload: {
    camera_id: string
    name: string
    rtsp_url: string
    enabled: boolean
  }): Promise<AdminCamera> {
    const response = await axios.post<AdminCamera>(`${API_BASE_URL}/cameras`, payload)
    return response.data
  },

  async updateCamera(
    cameraId: number,
    payload: { camera_id?: string; name?: string; rtsp_url?: string; enabled?: boolean },
  ): Promise<AdminCamera> {
    const response = await axios.patch<AdminCamera>(`${API_BASE_URL}/cameras/${cameraId}`, payload)
    return response.data
  },

  async deleteCamera(cameraId: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/cameras/${cameraId}`)
  },

  async listScenes(): Promise<SceneItem[]> {
    const response = await axios.get<SceneItem[]>(`${API_BASE_URL}/scenes`)
    return response.data
  },

  async createScene(payload: {
    camera_id: number
    name: string
    description?: string
    detect_api: string
    frame_interval_seconds?: number
    model_name?: string
  }): Promise<SceneItem> {
    const response = await axios.post<SceneItem>(`${API_BASE_URL}/scenes`, payload)
    return response.data
  },

  async updateScene(
    sceneId: number,
    payload: {
      name?: string
      description?: string
      detect_api?: string
      enabled?: boolean
      frame_interval_seconds?: number
      model_name?: string
    },
  ): Promise<SceneItem> {
    const response = await axios.patch<SceneItem>(`${API_BASE_URL}/scenes/${sceneId}`, payload)
    return response.data
  },

  async deleteScene(sceneId: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/scenes/${sceneId}`)
  },

  async listModels(detectApi?: string): Promise<string[]> {
    const response = await axios.get<{ models: string[] }>(`${API_BASE_URL}/models`, {
      params: detectApi ? { detect_api: detectApi } : undefined,
    })
    return response.data.models || []
  },
}
