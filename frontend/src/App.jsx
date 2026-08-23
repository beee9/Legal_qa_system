import React, { useState, useRef, useEffect, useCallback } from 'react'

// 会话消息结构
// { role: 'user' | 'assistant', content: string }

const API_BASE = '' // 开发环境经 vite 代理到后端

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const wsRef = useRef(null)
  const bottomRef = useRef(null)
  const messagesEndRef = useRef(null)

  // 创建会话
  const createSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/create_session`, { method: 'POST' })
      const data = await res.json()
      setSessionId(data.session_id)
      setMessages([])
    } catch (e) {
      console.error('创建会话失败:', e)
    }
  }, [])

  // 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 组件挂载时创建会话
  useEffect(() => {
    createSession()
    return () => wsRef.current?.close()
  }, [createSession])

  // 通过 WebSocket 流式请求
  const streamQuery = useCallback((query) => {
    const ws = new WebSocket(
      `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/stream`
    )
    wsRef.current = ws
    setLoading(true)

    // 先加一条助手占位消息，流式填充
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    ws.onopen = () => {
      ws.send(JSON.stringify({ query, source_filter: null, session_id: sessionId }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'start') {
        // 开始
      } else if (data.type === 'token' && data.token) {
        // 流式追加
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'assistant') {
            last.content += data.token
          }
          return next
        })
      } else if (data.type === 'end') {
        setLoading(false)
        ws.close()
      } else if (data.type === 'error') {
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'assistant' && !last.content) {
            last.content = '抱歉，回答出错了，请稍后重试。'
          }
          return next
        })
        setLoading(false)
        ws.close()
      }
    }

    ws.onerror = () => {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last && last.role === 'assistant' && !last.content) {
          last.content = '连接失败，请确认后端服务已启动。'
        }
        return next
      })
      setLoading(false)
    }

    ws.onclose = () => {
      setLoading(false)
    }
  }, [sessionId])

  // 提交查询
  const handleSend = async (e) => {
    e.preventDefault()
    const query = input.trim()
    if (!query || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: query }])
    setInput('')

    // 先走 REST 判断是否需要流式
    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
      })
      const data = await res.json()
      if (data.is_streaming) {
        streamQuery(query) // 需要 RAG/LLM，走 WebSocket 流式
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }])
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: '请求失败，请检查后端服务。' }])
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>⚖️ 法律智能问答系统</h1>
        <button className="new-btn" onClick={createSession}>新会话</button>
      </header>

      <main className="chat">
        {messages.length === 0 ? (
          <div className="welcome">
            <p>您好！我是法律智能问答助手</p>
            <p>覆盖《民法典》《劳动法》《劳动合同法》《公司法》《刑法》《民事诉讼法》</p>
            <p className="hint">试试问：<br />「民法典第五百零九条是什么？」<br />「合同违约了一般怎么处理？」</p>
          </div>
        ) : (
          <div className="messages">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <div className="bubble">{m.content}</div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      <form className="input-bar" onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="请输入您的法律问题…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? '…' : '发送'}
        </button>
      </form>

      <footer className="footer">
        本系统提供法律信息参考，不构成法律意见；涉及具体纠纷请咨询执业律师。
      </footer>
    </div>
  )
}
