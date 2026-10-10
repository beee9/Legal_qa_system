// 优化的前端主组件
// 主要改进：
// 1. 统一使用 WebSocket，简化 API 调用逻辑
// 2. 改进错误处理和加载状态
// 3. 优化消息显示和用户体验

import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  // 状态管理
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [sourceFilter, setSourceFilter] = useState('')
  const [availableSources, setAvailableSources] = useState([])
  const [error, setError] = useState(null)
  const [wsStatus, setWsStatus] = useState('disconnected') // disconnected, connecting, connected
  
  // WebSocket 引用
  const wsRef = useRef(null)
  const messagesEndRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 初始化：创建会话和获取法律来源
  useEffect(() => {
    const init = async () => {
      try {
        // 创建会话
        const sessionRes = await fetch('http://localhost:8003/api/create_session', {
          method: 'POST'
        })
        const sessionData = await sessionRes.json()
        setSessionId(sessionData.session_id)

        // 获取法律来源
        const sourcesRes = await fetch('http://localhost:8003/api/sources')
        const sourcesData = await sourcesRes.json()
        setAvailableSources(sourcesData.sources || [])
      } catch (err) {
        console.error('初始化失败:', err)
        setError('系统初始化失败，请刷新页面重试')
      }
    }

    init()
  }, [])

  // WebSocket 连接管理
  useEffect(() => {
    if (!sessionId) return

    const connectWebSocket = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        return // 已经连接
      }

      setWsStatus('connecting')
      const ws = new WebSocket('ws://localhost:8003/ws/query')

      ws.onopen = () => {
        console.log('✓ WebSocket 连接成功')
        setWsStatus('connected')
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        handleWebSocketMessage(data)
      }

      ws.onerror = (error) => {
        console.error('✗ WebSocket 错误:', error)
        setError('连接失败，正在尝试重连...')
      }

      ws.onclose = (event) => {
        console.log('WebSocket 断开:', event.code, event.reason)
        setWsStatus('disconnected')
        
        // 自动重连（最多尝试 5 次）
        if (reconnectAttemptsRef.current < 5) {
          reconnectAttemptsRef.current++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000)
          console.log(`${delay}ms 后尝试重连...`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, delay)
        } else {
          setError('连接已断开，请刷新页面重试')
        }
      }

      wsRef.current = ws
    }

    connectWebSocket()

    // 清理函数
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [sessionId])

  // 处理 WebSocket 消息
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'start':
        // 开始处理查询
        setIsLoading(true)
        setError(null)
        break

      case 'complete':
        // 收到完整答案（BM25 或问候语）
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: data.answer,
            timestamp: new Date().toISOString(),
            source: data.source || 'unknown',
            streaming: false
          }
        ])
        setIsLoading(false)
        break

      case 'token':
        // 收到流式内容片段（RAG）
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last && last.streaming) {
            // 追加到最后一条流式消息
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + data.content }
            ]
          } else {
            // 创建新的流式消息
            return [
              ...prev,
              {
                role: 'assistant',
                content: data.content,
                timestamp: new Date().toISOString(),
                source: 'rag',
                streaming: true
              }
            ]
          }
        })
        break

      case 'end':
        // 查询处理结束
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last && last.streaming) {
            return [
              ...prev.slice(0, -1),
              { ...last, streaming: false }
            ]
          }
          return prev
        })
        setIsLoading(false)
        console.log(`处理耗时: ${data.processing_time?.toFixed(2)}s`)
        break

      case 'error':
        // 错误信息
        setError(data.error)
        setIsLoading(false)
        setMessages(prev => [
          ...prev,
          {
            role: 'system',
            content: `错误: ${data.error}`,
            timestamp: new Date().toISOString(),
            isError: true
          }
        ])
        break
    }
  }

  // 发送查询
  const handleSend = () => {
    if (!inputValue.trim()) return
    
    if (wsStatus !== 'connected') {
      setError('连接未就绪，请稍候...')
      return
    }

    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])

    // 通过 WebSocket 发送查询
    try {
      wsRef.current.send(JSON.stringify({
        query: inputValue.trim(),
        source_filter: sourceFilter || null,
        session_id: sessionId
      }))
      setInputValue('')
      setError(null)
    } catch (err) {
      console.error('发送失败:', err)
      setError('发送失败，请重试')
      setIsLoading(false)
    }
  }

  // 清除历史
  const handleClearHistory = async () => {
    if (!sessionId) return

    try {
      await fetch(`http://localhost:8003/api/history/${sessionId}`, {
        method: 'DELETE'
      })
      setMessages([])
      setError(null)
    } catch (err) {
      console.error('清除历史失败:', err)
      setError('清除历史失败')
    }
  }

  // 按 Enter 发送
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 格式化时间
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <div className="app">
      {/* 头部 */}
      <header className="header">
        <h1>⚖️ 法律智能问答系统</h1>
        <div className="header-info">
          <span className={`status-indicator ${wsStatus}`}>
            {wsStatus === 'connected' ? '● 已连接' : 
             wsStatus === 'connecting' ? '⟳ 连接中...' : 
             '● 未连接'}
          </span>
          <button 
            onClick={handleClearHistory}
            className="btn-clear"
            disabled={messages.length === 0}
          >
            🗑️ 清除历史
          </button>
        </div>
      </header>

      {/* 错误提示 */}
      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* 聊天区域 */}
      <main className="chat-container">
        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>欢迎使用法律智能问答系统</h2>
              <p>您可以询问关于民法典、劳动法、公司法等法律问题</p>
              <div className="example-queries">
                <p>示例问题：</p>
                <button onClick={() => setInputValue('民法典第509条的内容是什么？')}>
                  民法典第509条的内容是什么？
                </button>
                <button onClick={() => setInputValue('合同违约怎么办？')}>
                  合同违约怎么办？
                </button>
                <button onClick={() => setInputValue('劳动合同期限有哪些规定？')}>
                  劳动合同期限有哪些规定？
                </button>
              </div>
            </div>
          )}

          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}
            >
              <div className="message-header">
                <span className="message-role">
                  {msg.role === 'user' ? '👤 您' : 
                   msg.role === 'system' ? '⚙️ 系统' : 
                   '🤖 助手'}
                </span>
                <span className="message-time">{formatTime(msg.timestamp)}</span>
                {msg.source && (
                  <span className="message-source">
                    {msg.source === 'bm25' ? '📚 精确匹配' :
                     msg.source === 'rag' ? '🧠 智能推理' :
                     msg.source === 'greeting' ? '👋 问候' : ''}
                  </span>
                )}
              </div>
              <div className="message-content">
                {msg.content}
                {msg.streaming && (
                  <span className="cursor-blink">▋</span>
                )}
              </div>
            </div>
          ))}

          {/* 加载指示器 */}
          {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="message assistant loading">
              <div className="message-header">
                <span className="message-role">🤖 助手</span>
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span className="loading-text">正在思考...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* 输入区域 */}
      <footer className="input-area">
        <div className="input-controls">
          <select 
            value={sourceFilter} 
            onChange={(e) => setSourceFilter(e.target.value)}
            className="source-select"
          >
            <option value="">所有法律</option>
            {availableSources.map(source => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
        </div>

        <div className="input-wrapper">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的法律问题... (按 Enter 发送，Shift+Enter 换行)"
            className="input-field"
            disabled={wsStatus !== 'connected'}
            rows="1"
          />
          <button 
            onClick={handleSend}
            disabled={!inputValue.trim() || wsStatus !== 'connected' || isLoading}
            className="btn-send"
          >
            {isLoading ? '⟳' : '发送'}
          </button>
        </div>

        <div className="footer-info">
          <small>
            本系统提供法律信息参考，不构成法律意见。如需专业法律建议，请咨询律师。
          </small>
        </div>
      </footer>
    </div>
  )
}

export default App
