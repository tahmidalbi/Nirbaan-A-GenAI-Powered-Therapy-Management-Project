import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../store/authStore';
import PatientHomework from '../components/PatientHomework';
import './PatientDashboard.css';

const PatientDashboard = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [activeSection, setActiveSection] = useState(null);
  const wsRef = useRef(null);

  // WebSocket connection for incoming calls
  useEffect(() => {
    if (!user?.id) return;

    const connectWebSocket = () => {
      const wsUrl = `ws://127.0.0.1:8000/ws/call/${user.id}?user_type=patient`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Patient WebSocket connected for incoming calls');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received WebSocket message:', message);

        if (message.type === 'incoming_call') {
          // Navigate to video call page when receiving incoming call
          // Note: Backend should include sessionId in the incoming_call message
          // For now, using caller_id as placeholder
          const sessionId = message.session_id || message.caller_id;
          navigate(`/video-call/${sessionId}`);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('Patient WebSocket disconnected');
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [user?.id, navigate]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleOCDToolsClick = () => {
    navigate('/patient/dashboard/tools/ocd');
  };

  return (
    <div className="patient-dashboard-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header with Navigation */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Nirbaan</h1>
          <nav className="nav-menu">
            <button
              className={`nav-btn ${activeSection === 'live_sessions' ? 'active' : ''}`}
              onClick={() => setActiveSection('live_sessions')}
            >
              Live Sessions
            </button>
            <button 
              className={`nav-btn ${activeSection === 'progress' ? 'active' : ''}`}
              onClick={() => setActiveSection('progress')}
            >
              Progress
            </button>
            <button 
              className={`nav-btn ${activeSection === 'homework' ? 'active' : ''}`}
              onClick={() => setActiveSection('homework')}
            >
              Homework
            </button>
            <button 
              className={`nav-btn ${activeSection === 'resources' ? 'active' : ''}`}
              onClick={() => setActiveSection('resources')}
            >
              Resources
            </button>
            <button 
              className="nav-btn"
              onClick={handleOCDToolsClick}
            >
              Tools
            </button>
            <button 
              className={`nav-btn ${activeSection === 'mindfulness' ? 'active' : ''}`}
              onClick={() => setActiveSection('mindfulness')}
            >
              Mindfulness
            </button>
            <button 
              className={`nav-btn ${activeSection === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveSection('chat')}
            >
              Chat
            </button>
          </nav>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      {/* Video Call Button - Only on landing page */}
      {!activeSection && (
        <button className="video-call-btn" title="Start Video Call">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
          </svg>
        </button>
      )}

      {/* Main Content - Empty sections */}
      <main className="dashboard-main">
        {activeSection === 'progress' && (
          <div className="empty-section">
            {/* Empty Progress section */}
          </div>
        )}

        {activeSection === 'homework' && (
          <div className="section-content">
            <PatientHomework />
          </div>
        )}

        {activeSection === 'resources' && (
          <div className="empty-section">
            {/* Empty Resources section */}
          </div>
        )}

        {activeSection === 'mindfulness' && (
          <div className="empty-section">
            {/* Empty Mindfulness section */}
          </div>
        )}

        {activeSection === 'live_sessions' && (
          <div className="empty-section">
            {/* Empty Sessions section */}
          </div>
        )}

        {activeSection === 'chat' && (
          <div className="empty-section">
            {/* Empty Chat section */}
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientDashboard;