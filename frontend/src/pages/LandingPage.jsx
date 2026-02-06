import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [animatedSections, setAnimatedSections] = useState(new Set());
  const [animatedWords, setAnimatedWords] = useState([]);
  const navigate = useNavigate();
  const sectionRefs = useRef([]);

  useEffect(() => {
    setTimeout(() => setIsVisible(true), 100);

    // Word-by-word animation for tagline
    const words = "Human-Centered AI for Therapist-Guided, Safe Mental Health Care".split(' ');
    words.forEach((_, index) => {
      setTimeout(() => {
        setAnimatedWords(prev => [...prev, index]);
      }, 500 + index * 150);
    });

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
      icon: 'I',
      title: 'Comprehensive Practice Management',
      description: 'Manage multiple patients, create personalized treatment plans, and organize group therapy sessions. Complete control over your therapeutic practice.',
      gradient: 'linear-gradient(135deg, #8BA89C 0%, #A0BDB1 100%)'
    },
    {
      icon: 'II',
      title: 'AI-Powered Patient Support',
      description: 'Your knowledge base powers an AI assistant that helps patients with therapy homework between sessions. You define the protocols, AI executes them.',
      gradient: 'linear-gradient(135deg, #93B0A4 0%, #A8C5B9 100%)'
    },
    {
      icon: 'III',
      title: 'Integrated Knowledge Base',
      description: 'Upload your scripts, research papers, blog links, and treatment protocols. Build a comprehensive therapeutic knowledge system tailored to your practice.',
      gradient: 'linear-gradient(135deg, #9BB8AC 0%, #B0CFC3 100%)'
    },
    {
      icon: 'IV',
      title: 'Video Therapy Sessions',
      description: 'Conduct secure teletherapy sessions with automatic transcription. Track patient progress with recorded session analytics and searchable transcripts.',
      gradient: 'linear-gradient(135deg, #8DAB9F 0%, #A2C0B4 100%)'
    },
    {
      icon: 'V',
      title: 'Crisis Intervention System',
      description: 'AI detects risk indicators and automatically alerts emergency personnel. Safety protocols you configure, automated vigilance you can trust.',
      gradient: 'linear-gradient(135deg, #95B3A7 0%, #AAC8BC 100%)'
    },
    {
      icon: 'VI',
      title: 'Specialized Treatment Protocols',
      description: 'ADHD task management, OCD exposure response prevention, cognitive behavioral worksheets. Evidence-based tools for specialized care.',
      gradient: 'linear-gradient(135deg, #8FAF9E 0%, #A4C4B3 100%)'
    },
    {
      icon: 'VII',
      title: 'Intelligent Progress Analytics',
      description: 'Advanced analytics examine patient progress, session transcripts, and treatment protocols. Transform data into actionable insights for better outcomes.',
      gradient: 'linear-gradient(135deg, #91B1A5 0%, #A6C6BA 100%)'
    },
    {
      icon: 'VIII',
      title: 'Multilingual Support',
      description: 'Conduct therapy in Bangla, English, or Banglish. Cultural sensitivity meets professional care with adaptive learning technology.',
      gradient: 'linear-gradient(135deg, #97B5A9 0%, #ACCABE 100%)'
    },
    {
      icon: 'IX',
      title: 'Guided Meditation Resources',
      description: 'Provide patients with mindfulness meditation sessions in their preferred language. Enhance therapy with evidence-based relaxation techniques.',
      gradient: 'linear-gradient(135deg, #9DB7AB 0%, #B2CCBF 100%)'
    }
  ];

  const taglineWords = "AI Powered Practice Management for Modern Therapists".split(' ');

  return (
    <div className="landing-container">
      {/* Vintage Geometric Background Patterns */}
      <div className="vintage-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-lines"></div>
        <div className="botanical-accent left-botanical"></div>
        <div className="botanical-accent right-botanical"></div>
      </div>

      {/* Header Navigation */}
      <header className="landing-header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-text">Nirbaan</span>
          </div>
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
            {taglineWords.map((word, index) => (
              <span
                key={index}
                className={`tagline-word ${animatedWords.includes(index) ? 'visible' : ''}`}
                style={{ animationDelay: `${index * 0.15}s` }}
              >
                {word}{' '}
              </span>
            ))}
          </p>
          <p className="hero-description">
            Elevate your therapeutic practice with intelligent patient management, AI-powered support systems, 
            and comprehensive tools designed for multi-patient care. Your expertise, amplified by technology.
          </p>
          <div className="hero-cta">
            <button className="btn-primary-large" onClick={() => navigate('/signup')}>
              Join as a Therapist
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
          <h2 className="section-title">Comprehensive Tools for Your Practice</h2>
          <p className="section-subtitle">
            Everything you need to manage patients, deliver care, and enhance outcomes
          </p>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div 
                key={index} 
                className={`feature-card ${animatedSections.has('features') ? 'animate-in' : ''}`}
                style={{ 
                  animationDelay: `${index * 0.1}s`,
                  background: feature.gradient
                }}
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
            <h2 className="cta-title">Transform Your Practice</h2>
            <p className="cta-description">
              Join a platform designed for therapists who want to scale their impact. Manage multiple patients, 
              leverage AI for administrative tasks, and focus on what matters most—delivering exceptional care.
            </p>
            <div className="cta-benefits">
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Add and manage unlimited patients with personalized treatment plans</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Upload your knowledge base to power AI-assisted patient support</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Organize group therapy sessions and track collective progress</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Automatic crisis detection with emergency intervention protocols</span>
              </div>
            </div>
            <button className="btn-join-platform" onClick={() => navigate('/signup')}>
              Start Your Practice Today
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>© 2026 Nirbaan - Empowering Therapists to Transform Lives</p>
      </footer>
    </div>
  );
};

export default LandingPage;
