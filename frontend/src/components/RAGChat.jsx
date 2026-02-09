import { useState } from 'react';
import { generateAnswer } from '../api/resource.api';
import './RAGChat.css';

const RAGChat = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [chatHistory, setChatHistory] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = { type: 'user', content: query };
    setChatHistory([...chatHistory, userMessage]);

    try {
      setLoading(true);
      setError('');
      
      const response = await generateAnswer(query);
      
      const aiMessage = {
        type: 'ai',
        content: response.answer,
        sources: response.sources,  // UPDATED: sources instead of citations
        chunksUsed: response.chunks_used,
      };
      
      setChatHistory([...chatHistory, userMessage, aiMessage]);
      setQuery('');
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rag-chat">
      <div className="chat-header">
        <h3>🤖 Nirbaan AI Assistant</h3>
        <p>Ask questions based on your knowledge base</p>
      </div>

      <div className="chat-messages">
        {chatHistory.length === 0 ? (
          <div className="empty-chat">
            <p>Start by asking a question about your uploaded documents.</p>
            <p className="example">Example: "What are the key steps in ERP therapy?"</p>
          </div>
        ) : (
          chatHistory.map((message, idx) => (
            <div key={idx} className={`message message-${message.type}`}>
              <div className="message-content">
                {message.type === 'user' ? (
                  <p>{message.content}</p>
                ) : (
                  <>
                    <p>{message.content}</p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="sources-section">
                        <strong>📚 Sources:</strong>
                        <div className="source-cards">
                          {message.sources.map((source, sidx) => (
                            <div key={sidx} className="source-card">
                              <div className="source-title">{source.resource_title}</div>
                              <div className="source-preview">{source.chunk_text}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
        
        {loading && (
          <div className="message message-ai">
            <div className="message-content loading">Thinking...</div>
          </div>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about your knowledge base..."
          disabled={loading}
          className="chat-input"
        />
        <button type="submit" disabled={loading || !query.trim()} className="send-btn">
          Send
        </button>
      </form>
    </div>
  );
};

export default RAGChat;