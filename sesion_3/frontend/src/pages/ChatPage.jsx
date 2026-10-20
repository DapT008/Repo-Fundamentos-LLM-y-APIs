import { useState, useRef, useEffect } from 'react'
import { sendMessage } from '../lib/api.js'
import { Send, Bot, User, AlertCircle } from 'lucide-react'

const C = {
  bg: '#0F1923',
  panel: '#1A2838',
  panel2: '#223548',
  cyan: '#00D4FF',
  gold: '#F5A623',
  green: '#00E676',
  text: '#E0E8F0',
  muted: '#7A95AA',
  border: '#2a3f54',
  error: '#ff5252',
}

const SUGGESTIONS = [
  '¿Qué es un JWT y cuándo usarlo?',
  'Explica el patrón Circuit Breaker',
  '¿Cómo funciona el rate limiting?',
  '¿Qué es el análisis TCO de un LLM?',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '¡Hola! Soy el asistente del LLM Security Lab. Puedo responder preguntas sobre seguridad, arquitectura y análisis de costos de sistemas LLM. ¿En qué te puedo ayudar?',
      ts: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [circuitState, setCircuitState] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    const msg = text || input.trim()
    if (!msg) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg, ts: new Date().toISOString() }])
    setLoading(true)
    try {
      const data = await sendMessage(msg)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        ts: new Date().toISOString(),
        meta: data,
      }])
      if (data.circuit_state) setCircuitState(data.circuit_state)
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Error al conectar con el backend'
      const isWaf = err.response?.status === 400 && errMsg.includes('WAF')
      setMessages(prev => [...prev, {
        role: 'error',
        content: errMsg,
        isWaf,
        ts: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <Bot size={20} color={C.cyan} />
        <span style={{ marginLeft: 8, fontWeight: 600 }}>Chat Seguro con LLM</span>
        {circuitState && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '0.75rem',
            padding: '3px 8px',
            borderRadius: 4,
            background: circuitState === 'CERRADO' ? 'rgba(0,230,118,0.15)' : 'rgba(255,82,82,0.15)',
            color: circuitState === 'CERRADO' ? C.green : C.error,
            border: `1px solid ${circuitState === 'CERRADO' ? 'rgba(0,230,118,0.3)' : 'rgba(255,82,82,0.3)'}`,
          }}>
            Circuit: {circuitState}
          </span>
        )}
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div style={styles.typing}>
            <Bot size={14} color={C.muted} style={{ marginRight: 6 }} />
            <span style={{ color: C.muted, fontSize: '0.85rem' }}>Generando respuesta...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length === 1 && (
        <div style={styles.suggestions}>
          {SUGGESTIONS.map((s, i) => (
            <button key={i} onClick={() => send(s)} style={styles.suggBtn}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={styles.inputArea}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Escribe tu pregunta... (Enter para enviar)"
          rows={2}
          style={styles.textarea}
          disabled={loading}
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          style={styles.sendBtn}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const isError = msg.role === 'error'

  return (
    <div style={{
      ...styles.bubble,
      alignSelf: isUser ? 'flex-end' : 'flex-start',
      maxWidth: isUser ? '70%' : '80%',
    }}>
      <div style={styles.bubbleHeader}>
        {isUser
          ? <User size={14} color="#7A95AA" />
          : isError
            ? <AlertCircle size={14} color="#ff5252" />
            : <Bot size={14} color="#00D4FF" />}
        <span style={{
          fontSize: '0.7rem',
          color: '#7A95AA',
          marginLeft: 4,
        }}>
          {new Date(msg.ts).toLocaleTimeString()}
        </span>
        {msg.isWaf && (
          <span style={styles.wafBadge}>🛡 WAF Block</span>
        )}
      </div>
      <div style={{
        ...styles.bubbleContent,
        background: isUser ? '#0d2235' : isError ? 'rgba(255,82,82,0.08)' : '#1A2838',
        border: `1px solid ${isUser ? '#1a3a55' : isError ? 'rgba(255,82,82,0.2)' : '#2a3f54'}`,
        color: isError ? '#ff5252' : '#E0E8F0',
      }}>
        {msg.content}
      </div>
      {msg.meta && (
        <div style={styles.meta}>
          {msg.meta.latency_ms && `${msg.meta.latency_ms}ms`}
          {msg.meta.model && ` · ${msg.meta.model}`}
        </div>
      )}
    </div>
  )
}

const styles = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#0F1923',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '14px 20px',
    borderBottom: '1px solid #2a3f54',
    background: '#1A2838',
    color: '#E0E8F0',
    fontWeight: 500,
    flexShrink: 0,
  },
  messages: {
    flex: 1,
    overflow: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  bubble: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  bubbleHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  bubbleContent: {
    borderRadius: 10,
    padding: '10px 14px',
    fontSize: '0.9rem',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  meta: {
    fontSize: '0.7rem',
    color: '#4a6580',
    paddingLeft: 4,
  },
  wafBadge: {
    marginLeft: 'auto',
    fontSize: '0.7rem',
    background: 'rgba(255,82,82,0.15)',
    color: '#ff5252',
    padding: '2px 6px',
    borderRadius: 4,
  },
  typing: {
    display: 'flex',
    alignItems: 'center',
    paddingLeft: 4,
  },
  suggestions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    padding: '0 20px 12px',
  },
  suggBtn: {
    background: '#1A2838',
    border: '1px solid #2a3f54',
    borderRadius: 20,
    color: '#7A95AA',
    padding: '6px 14px',
    fontSize: '0.8rem',
    cursor: 'pointer',
  },
  inputArea: {
    display: 'flex',
    gap: 8,
    padding: '12px 20px',
    borderTop: '1px solid #2a3f54',
    background: '#1A2838',
    flexShrink: 0,
  },
  textarea: {
    flex: 1,
    background: '#0d1e2d',
    border: '1px solid #2a3f54',
    borderRadius: 8,
    color: '#E0E8F0',
    padding: '10px 14px',
    fontSize: '0.9rem',
    resize: 'none',
    outline: 'none',
    fontFamily: 'inherit',
    lineHeight: 1.5,
  },
  sendBtn: {
    background: '#00D4FF',
    border: 'none',
    borderRadius: 8,
    color: '#0F1923',
    width: 42,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
}
