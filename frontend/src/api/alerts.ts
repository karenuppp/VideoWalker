import axios from 'axios'
import type { Alert, AlertStats } from '../types/alert'

const API_BASE_URL = '/api/v1'

export const alertsApi = {
  async getAlerts(params?: {
    skip?: number
    limit?: number
    camera_id?: number
    status?: string
    alert_type?: string
  }): Promise<Alert[]> {
    const response = await axios.get<Alert[]>(`${API_BASE_URL}/alerts`, { params })
    return response.data
  },

  async getAlertStats(): Promise<AlertStats> {
    const response = await axios.get<AlertStats>(`${API_BASE_URL}/alerts/stats`)
    return response.data
  },

  async getAlertById(id: number): Promise<Alert> {
    const response = await axios.get<Alert>(`${API_BASE_URL}/alerts/${id}`)
    return response.data
  },

  async updateAlertStatus(id: number, status: string): Promise<Alert> {
    const response = await axios.put<Alert>(`${API_BASE_URL}/alerts/${id}/status`, { status })
    return response.data
  },

  async deleteAlert(id: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/alerts/${id}`)
  }
}