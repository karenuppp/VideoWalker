/**
 * WebSocket service for realtime alerts.
 */

export type WebSocketMessage = {
  type: 'alert' | 'alert_update' | 'stats' | 'pong'
  data: any
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private heartbeatInterval: number | null = null
  private isConnecting = false
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  constructor(private url: string) {}

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true
    console.log('Connecting WebSocket...', this.url)

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('WebSocket message parse failed:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.isConnecting = false
        this.stopHeartbeat()
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('WebSocket connect failed:', error)
      this.isConnecting = false
      this.attemptReconnect()
    }
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.listeners.clear()
  }

  private handleMessage(message: WebSocketMessage) {
    const { type, data } = message

    switch (type) {
      case 'alert':
        console.log('Alert received', data)
        this.emit('alert', data)
        break
      case 'alert_update':
        console.log('Alert update received', data)
        this.emit('alert_update', data)
        break
      case 'stats':
        console.log('Stats received', data)
        this.emit('stats', data)
        break
      case 'pong':
        break
      default:
        console.warn('Unknown WebSocket message type:', type)
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket reconnect failed: max attempts reached')
      return
    }

    this.reconnectAttempts++
    console.log(`WebSocket reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connect()
    }, this.reconnectDelay)
  }

  private startHeartbeat() {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback: (data: any) => void) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.delete(callback)
    }
  }

  private emit(event: string, data: any) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(callback => callback(data))
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

const wsHost = window.location.port === '5173'
  ? `${window.location.hostname}:9002`
  : window.location.host
const wsUrl = `ws://${wsHost}/ws/alerts`
export const websocketService = new WebSocketService(wsUrl)
