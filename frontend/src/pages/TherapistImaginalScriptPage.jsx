import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  startImaginalRun,
  reviewImaginalRun,
  listApprovedByItem,
  getAudioUrl,
} from '../api/imaginal-generator.api';
import './TherapistERPPatientList.css';
import './TherapistImaginalScriptPage.css';

const TherapistImaginalScriptPage = () => {
  const navigate = useNavigate();
  const { patientId, itemId } = useParams();
  const location = useLocation();
  const { logout, user } = useAuthStore();

  const patientName = location.state?.patientName || 'Patient';
  const patientEmail = location.state?.patientEmail || '';
  const obsession = location.state?.obsession || '';
  const compulsions = location.state?.compulsions || [];

  const [activeTab, setActiveTab] = useState('generator');

  // ── Script Generator state ──
  const [sgFeared, setSgFeared] = useState('');
  const [sgIntensity, setSgIntensity] = useState('');
  const [sgSubtype, setSgSubtype] = useState('');
  const [sgRun, setSgRun] = useState(null);
  const [sgLoading, setSgLoading] = useState(false);
  const [sgError, setSgError] = useState('');
  const [sgFeedback, setSgFeedback] = useState('');
  const [sgFeedbackVisible, setSgFeedbackVisible] = useState(false);

  // ── Past Scripts state ──
  const [pastScripts, setPastScripts] = useState([]);
  const [pastLoading, setPastLoading] = useState(false);
  const [pastError, setPastError] = useState('');
  const [expandedScript, setExpandedScript] = useState(null);

  const loadPastScripts = useCallback(async () => {
    setPastLoading(true);
    setPastError('');
    try {
      const { data } = await listApprovedByItem(itemId);
      setPastScripts(data);
    } catch (err) {
      setPastError(typeof err === 'string' ? err : 'Failed to load past scripts.');
    } finally {
      setPastLoading(false);
    }
  }, [itemId]);

  useEffect(() => {
    if (activeTab === 'past') loadPastScripts();
  }, [activeTab, loadPastScripts]);

  const handleBack = () =>
    navigate(`/therapist/dashboard/imaginal/patient/${patientId}`, {
      state: { patientName, patientEmail },
    });

  // ── Generate handler ──
  const handleGenerate = async () => {
    setSgError('');
    setSgLoading(true);
    try {
      const { data } = await startImaginalRun({
        patient_id: Number(patientId),
        therapist_id: Number(user?.id),
        erp_item_id: Number(itemId),
        feared_consequence: sgFeared.trim(),
        script_intensity: sgIntensity.trim(),
        subtype: sgSubtype.trim() || null,
      });
      setSgRun(data);
    } catch (err) {
      setSgError(typeof err === 'string' ? err : 'Failed to start generation.');
    } finally {
      setSgLoading(false);
    }
  };

  const handleApprove = async () => {
    setSgError('');
    setSgLoading(true);
    try {
      const { data } = await reviewImaginalRun({
        thread_id: sgRun.thread_id,
        approved: true,
      });
      setSgRun(data);
    } catch (err) {
      setSgError(typeof err === 'string' ? err : 'Failed to approve script.');
    } finally {
      setSgLoading(false);
    }
  };

  const handleReject = async () => {
    setSgError('');
    setSgLoading(true);
    setSgFeedbackVisible(false);
    try {
      const { data } = await reviewImaginalRun({
        thread_id: sgRun.thread_id,
        approved: false,
        feedback: sgFeedback.trim(),
      });
      setSgRun(data);
      setSgFeedback('');
    } catch (err) {
      setSgError(typeof err === 'string' ? err : 'Failed to submit feedback.');
    } finally {
      setSgLoading(false);
    }
  };

  const resetGenerator = () => {
    setSgRun(null);
    setSgFeared('');
    setSgIntensity('');
    setSgSubtype('');
    setSgFeedback('');
    setSgFeedbackVisible(false);
    setSgError('');
  };

  return (
    <div className="tisp-container">
      <div className="terp-bg">
        <div className="terp-bg-pattern" />
        <div className="terp-deco terp-deco-top" />
        <div className="terp-deco terp-deco-bottom" />
      </div>

      <header className="terp-header">
        <div className="terp-header-inner">
          <button className="terp-ghost-btn" onClick={handleBack}>← Back</button>
          <div className="terp-header-title">
            <h1 className="terp-logo">Imaginal Script</h1>
            <p className="terp-header-sub">
              {patientName}{patientEmail ? ` · ${patientEmail}` : ''}
            </p>
          </div>
          <button className="terp-ghost-btn" onClick={() => { logout(); navigate('/select-role'); }}>
            Logout
          </button>
        </div>
      </header>

      <main className="tisp-main">
        {/* Obsession context */}
        <div className="tisp-context">
          <p className="tisp-context-label">Obsession</p>
          <p className="tisp-context-text">{obsession}</p>
          {compulsions.length > 0 && (
            <>
              <p className="tisp-context-label">Compulsions</p>
              <p className="tisp-context-text">{compulsions.join('; ')}</p>
            </>
          )}
        </div>

        {/* Tabs */}
        <div className="tisp-tabs">
          <button
            className={`tisp-tab ${activeTab === 'generator' ? 'tisp-tab--active' : ''}`}
            onClick={() => setActiveTab('generator')}
          >
            Script Generator
          </button>
          <button
            className={`tisp-tab ${activeTab === 'past' ? 'tisp-tab--active' : ''}`}
            onClick={() => setActiveTab('past')}
          >
            Past Scripts
          </button>
        </div>

        {/* ═══ Script Generator Tab ═══ */}
        {activeTab === 'generator' && (
          <div className="tisp-panel">
            {sgError && <div className="tisp-error">{sgError}</div>}

            {/* Form */}
            {!sgRun && !sgLoading && (
              <div className="tisp-form">
                <p className="tisp-form-intro">
                  Fill in the fields below to generate an AI imaginal exposure script.
                </p>

                <label className="tisp-label">Feared Consequence *</label>
                <textarea
                  className="tisp-textarea"
                  rows={3}
                  placeholder="e.g. I will contaminate my family and they will get seriously ill…"
                  value={sgFeared}
                  onChange={(e) => setSgFeared(e.target.value)}
                />

                <label className="tisp-label">Script Intensity *</label>
                <input
                  className="tisp-input"
                  type="text"
                  placeholder="e.g. 7/10"
                  value={sgIntensity}
                  onChange={(e) => setSgIntensity(e.target.value)}
                />

                <label className="tisp-label">Subtype (optional)</label>
                <input
                  className="tisp-input"
                  type="text"
                  placeholder="e.g. contamination, checking…"
                  value={sgSubtype}
                  onChange={(e) => setSgSubtype(e.target.value)}
                />

                <button
                  className="tisp-btn tisp-btn--primary"
                  disabled={!sgFeared.trim() || !sgIntensity.trim()}
                  onClick={handleGenerate}
                >
                  Generate Script
                </button>
              </div>
            )}

            {/* Spinner */}
            {sgLoading && (
              <div className="tisp-generating">
                <div className="tisp-spinner" />
                <p>Running LangGraph agent… this may take a moment.</p>
              </div>
            )}

            {/* Script review */}
            {sgRun && !sgLoading && sgRun.interrupt_required && (
              <div className="tisp-review">
                <h3 className="tisp-review-title">Generated Script — Version {sgRun.version_no}</h3>
                <pre className="tisp-script-pre">{sgRun.script_text}</pre>

                {sgFeedbackVisible && (
                  <div className="tisp-feedback">
                    <label className="tisp-label">What didn't you like?</label>
                    <textarea
                      className="tisp-textarea"
                      rows={3}
                      placeholder="e.g. Too graphic, needs more focus on contamination fear…"
                      value={sgFeedback}
                      onChange={(e) => setSgFeedback(e.target.value)}
                    />
                    <button
                      className="tisp-btn tisp-btn--reject"
                      disabled={!sgFeedback.trim()}
                      onClick={handleReject}
                    >
                      Submit &amp; Regenerate
                    </button>
                  </div>
                )}

                {!sgFeedbackVisible && (
                  <div className="tisp-actions">
                    <button className="tisp-btn tisp-btn--primary" onClick={handleApprove}>
                      ✓ Approve
                    </button>
                    <button
                      className="tisp-btn tisp-btn--reject"
                      onClick={() => setSgFeedbackVisible(true)}
                    >
                      ✕ Reject
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Done */}
            {sgRun && !sgLoading && !sgRun.interrupt_required && (
              <div className="tisp-done">
                <div className="tisp-done-icon">✓</div>
                <h3>Script Approved</h3>
                <p>The script has been saved and audio generated for the patient.</p>
                {sgRun.approved_script_id && (
                  <div className="tisp-audio-box">
                    <span className="tisp-label">Preview Audio</span>
                    {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                    <audio
                      controls
                      src={getAudioUrl(sgRun.approved_script_id)}
                      className="tisp-audio-player"
                    />
                  </div>
                )}
                <button className="tisp-btn tisp-btn--primary" style={{ marginTop: '1.5rem' }} onClick={resetGenerator}>
                  Generate Another Script
                </button>
              </div>
            )}
          </div>
        )}

        {/* ═══ Past Scripts Tab ═══ */}
        {activeTab === 'past' && (
          <div className="tisp-panel">
            {pastError && <div className="tisp-error">{pastError}</div>}

            {pastLoading ? (
              <div className="tisp-generating"><p>Loading past scripts…</p></div>
            ) : pastScripts.length === 0 ? (
              <div className="tisp-empty">
                <p>No approved scripts for this obsession yet.</p>
              </div>
            ) : (
              <div className="tisp-past-list">
                {pastScripts.map((script, idx) => (
                  <div key={script.id} className="tisp-past-card">
                    <div
                      className="tisp-past-header"
                      onClick={() => setExpandedScript(expandedScript === script.id ? null : script.id)}
                    >
                      <span className="tisp-past-num">Script {idx + 1}</span>
                      {script.subtype && <span className="tisp-past-tag">{script.subtype}</span>}
                      <span className="tisp-past-date">
                        {new Date(script.created_at).toLocaleDateString(undefined, {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </span>
                      <span className="tisp-past-toggle">
                        {expandedScript === script.id ? '▾' : '▸'}
                      </span>
                    </div>

                    {expandedScript === script.id && (
                      <div className="tisp-past-body">
                        {/* Audio */}
                        <div className="tisp-audio-box">
                          <span className="tisp-label">Audio</span>
                          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                          <audio
                            controls
                            src={getAudioUrl(script.id)}
                            className="tisp-audio-player"
                          />
                        </div>
                        {/* Script text */}
                        <div className="tisp-past-script-text">
                          <span className="tisp-label">Script Text</span>
                          <pre className="tisp-script-pre">{script.approved_script}</pre>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default TherapistImaginalScriptPage;
