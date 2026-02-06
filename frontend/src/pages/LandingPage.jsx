import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [animatedSections, setAnimatedSections] = useState(new Set());
  const navigate = useNavigate();
  const sectionRefs = useRef([]);

  useEffect(() => {
    setTimeout(() => setIsVisible(true), 100);

    // Scroll animation observer
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = entry.target.getAttribute('data-section');
            if (index) {
              setAnimatedSections((prev) => new Set([...prev, index]));
            }
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -50px 0px' }
    );

    sectionRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    return () => observer.disconnect();
  }, []);

  const addToRefs = (el) => {
    if (el && !sectionRefs.current.includes(el)) {
      sectionRefs.current.push(el);
    }
  };

  const features = [
    {
      icon: '🧠',
      title: 'AI-Powered Therapy Support',
      description: 'Advanced AI agents trained on therapist knowledge bases to provide personalized, safe assistance grounded in professional expertise.'
    },
    {
      icon: '👥',
      title: 'Multi-Therapist Platform',
      description: 'Connect multiple therapists with their patients in a secure, HIPAA-compliant environment designed for collaborative care.'
    },
    {
      icon: '📊',
      title: 'Progress Tracking',
      description: 'Comprehensive patient progress monitoring with RAG-powered analysis of therapy sessions, homework completion, and manual updates.'
    },
    {
      icon: '🎯',
      title: 'Specialized Care Modules',
      description: 'Tailored interventions for ADHD, OCD, and other conditions with evidence-based games, exposure therapy tools, and cognitive worksheets.'
    },
    {
      icon: '🔒',
      title: 'Safety First',
      description: 'Built-in crisis detection with uncertainty scoring. Automatic human escalation when AI detects self-harm or suicide risk.'
    },
    {
      icon: '🌐',
      title: 'Multilingual Support',
      description: 'Full support for Banglish and multiple languages, making mental health care accessible to diverse communities.'
    },
    {
      icon: '📹',
      title: 'Video Therapy Sessions',
      description: 'Integrated video calling with automatic transcription and secure storage for continuity of care and progress analysis.'
    },
    {
      icon: '🤖',
      title: 'Federated Learning',
      description: 'Privacy-preserving AI personalization that adapts to each patient while maintaining data security and confidentiality.'
    }
  ];

  return (
    <div className="landing-container">
      {/* Header Navigation */}
      <header className="landing-header">
        <div className="header-content">
          <div className="logo">Nirbaan</div>
          <nav className="nav-buttons">
            <button className="btn-nav btn-login" onClick={() => navigate('/login')}>
              Login
            </button>
            <button className="btn-nav btn-signup" onClick={() => navigate('/signup')}>
              Sign Up
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className={`hero-section ${isVisible ? 'visible' : ''}`}>
        <div className="hero-content">
          <h1 className="hero-title">Nirbaan</h1>
          <p className="hero-tagline">
            Human-Centered AI for Therapist-Guided, Safe Mental Health Care
          </p>
          <p className="hero-description">
            Empowering therapists with AI-driven tools to deliver personalized, 
            evidence-based care while maintaining the critical human connection.
          </p>
          <div className="hero-cta">
            <button className="btn-primary-large" onClick={() => navigate('/signup')}>
              Get Started Today
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section 
        className={`features-section ${animatedSections.has('features') ? 'animate-in' : ''}`}
        ref={addToRefs}
        data-section="features"
      >
        <div className="section-container">
          <h2 className="section-title">Comprehensive Mental Health Care Platform</h2>
          <p className="section-subtitle">
            Everything therapists need to provide exceptional, technology-enhanced care
          </p>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div 
                key={index} 
                className={`feature-card ${animatedSections.has('features') ? 'animate-in' : ''}`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="feature-icon">{feature.icon}</div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Therapist CTA Section */}
      <section 
        className={`therapist-cta-section ${animatedSections.has('cta') ? 'animate-in' : ''}`}
        ref={addToRefs}
        data-section="cta"
      >
        <div className="cta-container">
          <div className="cta-content">
            <h2 className="cta-title">Join Our Growing Network of Therapists</h2>
            <p className="cta-description">
              Transform your practice with AI-powered tools that enhance, not replace, your expertise. 
              Manage patients, track progress, conduct video sessions, and leverage your knowledge base 
              with cutting-edge technology designed specifically for mental health professionals.
            </p>
            <div className="cta-benefits">
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Upload your entire knowledge base and treatment protocols</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Create custom AI agents tailored to each patient</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Video therapy with automatic transcription and analysis</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>24/7 patient support grounded in your expertise</span>
              </div>
            </div>
            <button className="btn-join-platform" onClick={() => navigate('/signup')}>
              Join the Platform
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>© 2026 Nirbaan - A sanctuary for healing and growth</p>
      </footer>
    </div>
  );
};

export default LandingPage;
