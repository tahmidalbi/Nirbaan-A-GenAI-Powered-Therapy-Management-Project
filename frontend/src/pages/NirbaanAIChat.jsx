import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { sendNirbaanAIMessage, listNirbaanAIThreads, getNirbaanAIThread } from '../api/nirbaanai.api';
import './NirbaanAIChat.css';

// ── Flower canvas animation ──────────────────────────────────────────────────
const PETAL_COUNT = 55;

function randomBetween(a, b) {
  return a + Math.random() * (b - a);
}

function useFlowerCanvas(canvasRef) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let animId;
    let flowers = [];

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    function createFlower() {
      const size = randomBetween(12, 24);
      return {
        x: randomBetween(0, canvas.width),
        y: randomBetween(-60, -10),
        size,
        speed: randomBetween(1.2, 2.8),
        swing: randomBetween(0.4, 1.2),
        swingOffset: randomBetween(0, Math.PI * 2),
        swingSpeed: randomBetween(0.01, 0.025),
        rotation: randomBetween(0, Math.PI * 2),
        rotSpeed: randomBetween(-0.025, 0.025),
        opacity: randomBetween(0.6, 0.95),
        hue: randomBetween(300, 340), // pink-magenta petals
      };
    }

    flowers = Array.from({ length: PETAL_COUNT }, createFlower);

    function drawPetal(ctx, size, hue, opacity) {
      ctx.save();
      ctx.globalAlpha = opacity;
      const petalCount = 5;
      for (let i = 0; i < petalCount; i++) {
        const angle = (i / petalCount) * Math.PI * 2;
        ctx.save();
        ctx.rotate(angle);
        ctx.beginPath();
        ctx.ellipse(0, -size * 0.5, size * 0.28, size * 0.55, 0, 0, Math.PI * 2);
        ctx.fillStyle = `hsl(${hue}, 85%, 75%)`;
        ctx.fill();
        ctx.restore();
      }
      // centre dot
      ctx.beginPath();
      ctx.arc(0, 0, size * 0.15, 0, Math.PI * 2);
      ctx.fillStyle = `hsl(50, 100%, 80%)`;
      ctx.fill();
      ctx.restore();
    }

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      flowers.forEach((f) => {
        f.y += f.speed;
        f.x += Math.sin(f.swingOffset) * f.swing;
        f.swingOffset += f.swingSpeed;
        f.rotation += f.rotSpeed;

        if (f.y > canvas.height + 30) {
          Object.assign(f, createFlower(), { x: randomBetween(0, canvas.width) });
        }

        ctx.save();
        ctx.translate(f.x, f.y);
        ctx.rotate(f.rotation);
        drawPetal(ctx, f.size, f.hue, f.opacity);
        ctx.restore();
      });

      animId = requestAnimationFrame(animate);
    }

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [canvasRef]);
}

// ── Main component ────────────────────────────────────────────────────────────
export default function NirbaanAIChat() {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  useFlowerCanvas(canvasRef);

  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Load thread list on mount
  useEffect(() => {
    listNirbaanAIThreads()
      .then(setThreads)
      .catch(() => {});
  }, []);

  // Scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadThread = useCallback(async (threadId) => {
    try {
      setLoading(true);
      const data = await getNirbaanAIThread(threadId);
      setActiveThreadId(threadId);
      setMessages(data.messages || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setSidebarOpen(false);
    }
  }, []);

  const startNewChat = () => {
    setActiveThreadId(null);
    setMessages([]);
    setSidebarOpen(false);
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendNirbaanAIMessage({ message: text, thread_id: activeThreadId });

      // If this is a new thread, capture the ID and refresh sidebar list
      if (!activeThreadId) {
        setActiveThreadId(res.thread_id);
        listNirbaanAIThreads().then(setThreads).catch(() => {});
      }

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== userMsg.id), // remove optimistic
        res.user_message,
        res.assistant_message,
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="nai-root">
      {/* Animated flower canvas */}
      <canvas ref={canvasRef} className="nai-canvas" />

      {/* Top bar */}
      <header className="nai-header">
        <button className="nai-back-btn" onClick={() => navigate('/patient/dashboard')}>
          ← Back
        </button>
        <div className="nai-header-title">
          <span className="nai-logo-icon">🌸</span>
          <span className="nai-logo-text">NirbaanAI</span>
        </div>
        <button className="nai-sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)}>
          ☰ History
        </button>
      </header>

      {/* Thread sidebar */}
      <aside className={`nai-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="nai-sidebar-header">
          <span>Conversations</span>
          <button className="nai-new-btn" onClick={startNewChat}>+ New</button>
        </div>
        <ul className="nai-thread-list">
          {threads.length === 0 && (
            <li className="nai-thread-empty">No conversations yet</li>
          )}
          {threads.map((t) => (
            <li
              key={t.id}
              className={`nai-thread-item ${t.id === activeThreadId ? 'active' : ''}`}
              onClick={() => loadThread(t.id)}
            >
              <span className="nai-thread-icon">💬</span>
              <span className="nai-thread-label">
                {t.title || `Chat #${t.id}`}
              </span>
            </li>
          ))}
        </ul>
      </aside>

      {/* Overlay to close sidebar on mobile */}
      {sidebarOpen && <div className="nai-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* Main chat area */}
      <main className="nai-main">
        <div className="nai-chat-window">
          {messages.length === 0 && !loading && (
            <div className="nai-welcome">
              <div className="nai-welcome-icon">🌿</div>
              <h2>Hello, I'm NirbaanAI</h2>
              <p>Your personal psychoeducation companion.<br />Ask me anything about OCD, anxiety, or your therapy journey.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`nai-bubble-row ${msg.role === 'user' ? 'user' : 'assistant'}`}
            >
              {msg.role === 'assistant' && (
                <div className="nai-avatar">🌸</div>
              )}
              <div className={`nai-bubble ${msg.role}`}>
                <p>{msg.content}</p>
                <span className="nai-ts">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              {msg.role === 'user' && (
                <div className="nai-avatar user-avatar">You</div>
              )}
            </div>
          ))}

          {loading && (
            <div className="nai-bubble-row assistant">
              <div className="nai-avatar">🌸</div>
              <div className="nai-bubble assistant nai-typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="nai-input-bar">
          <textarea
            ref={inputRef}
            className="nai-input"
            rows={2}
            placeholder="Type your message… (Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            className="nai-send-btn"
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            {loading ? '…' : '➤'}
          </button>
        </div>
      </main>
    </div>
  );
}
