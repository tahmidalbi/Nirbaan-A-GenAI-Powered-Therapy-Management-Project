import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { listPatientApprovedScripts, getAudioUrl } from '../api/imaginal-generator.api';
import { listERPItems } from '../api/erp.api';
import './PatientImaginalScripts.css';

const PatientImaginalScripts = () => {
  const navigate = useNavigate();
  const { logout, user, _hasHydrated } = useAuthStore();
  const [scripts, setScripts] = useState([]);
  const [erpItemsMap, setErpItemsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedObsId, setExpandedObsId] = useState(null);
  const [expandedScriptId, setExpandedScriptId] = useState(null);

  useEffect(() => {
    if (!_hasHydrated) return; // wait for Zustand to finish reading localStorage
    if (!user?.id) {
      setLoading(false);
      return;
    }
    Promise.all([listPatientApprovedScripts(user.id), listERPItems()])
      .then(([scriptsRes, itemsRes]) => {
        setScripts(scriptsRes.data);
        const map = {};
        (itemsRes.data || []).forEach((item) => { map[item.id] = item; });
        setErpItemsMap(map);
      })
      .catch((err) => setError(typeof err === 'string' ? err : 'Failed to load scripts.'))
      .finally(() => setLoading(false));
  }, [user, _hasHydrated]);

  // Group scripts by erp_item_id (preserving first-seen order)
  const orderedItemIds = [];
  const byItem = {};
  scripts.forEach((s) => {
    if (!byItem[s.erp_item_id]) {
      orderedItemIds.push(s.erp_item_id);
      byItem[s.erp_item_id] = [];
    }
    byItem[s.erp_item_id].push(s);
  });

  return (
    <div className="pis-container">
      {/* Background */}
      <div className="dashboard-background">
        <div className="geometric-pattern" />
        <div className="art-deco-line art-deco-line-top" />
        <div className="art-deco-line art-deco-line-bottom" />
      </div>

      <header className="pis-header">
        <div className="pis-header-inner">
          <button className="pis-ghost-btn" onClick={() => navigate('/patient/dashboard/tools/ocd')}>
            ← Back
          </button>
          <h1 className="pis-logo">Imaginal Scripts</h1>
          <button className="pis-ghost-btn" onClick={() => { logout(); navigate('/login'); }}>
            Logout
          </button>
        </div>
      </header>

      <main className="pis-main">
        <p className="pis-intro">
          Your therapist-approved imaginal exposure scripts. Tap a script to listen and read.
        </p>

        {error && <div className="pis-error">{error}</div>}

        {loading ? (
          <div className="pis-loading">Loading scripts…</div>
        ) : scripts.length === 0 ? (
          <div className="pis-empty">
            <div className="pis-empty-icon">💭</div>
            <h3>No scripts yet</h3>
            <p>Your therapist will create imaginal exposure scripts for you.</p>
          </div>
        ) : (
          <div className="pis-list">
            {orderedItemIds.map((itemId) => {
              const obsText = erpItemsMap[itemId]?.obsession || `Obsession #${itemId}`;
              const itemScripts = byItem[itemId];
              const isObsOpen = expandedObsId === itemId;
              return (
                <div key={itemId} className={`pis-card ${isObsOpen ? 'pis-card--open' : ''}`}>
                  <div
                    className="pis-card-header"
                    onClick={() => {
                      setExpandedObsId(isObsOpen ? null : itemId);
                      setExpandedScriptId(null);
                    }}
                  >
                    <span className="pis-card-num pis-card-obs-label">{obsText}</span>
                    <span className="pis-card-tag">{itemScripts.length} script{itemScripts.length !== 1 ? 's' : ''}</span>
                    <span className="pis-card-toggle" style={{ marginLeft: 'auto' }}>{isObsOpen ? '▾' : '▸'}</span>
                  </div>

                  {isObsOpen && (
                    <div className="pis-card-body pis-obs-scripts">
                      {itemScripts.map((script, idx) => {
                        const isScriptOpen = expandedScriptId === script.id;
                        return (
                          <div key={script.id} className={`pis-card pis-card--nested ${isScriptOpen ? 'pis-card--open' : ''}`}>
                            <div
                              className="pis-card-header"
                              onClick={() => setExpandedScriptId(isScriptOpen ? null : script.id)}
                            >
                              <span className="pis-card-num">Script {idx + 1}</span>
                              {script.subtype && <span className="pis-card-tag">{script.subtype}</span>}
                              <span className="pis-card-date">
                                {new Date(script.created_at).toLocaleDateString(undefined, {
                                  day: 'numeric',
                                  month: 'short',
                                  year: 'numeric',
                                })}
                              </span>
                              <span className="pis-card-toggle">{isScriptOpen ? '▾' : '▸'}</span>
                            </div>

                            {isScriptOpen && (
                              <div className="pis-card-body">
                                {/* Audio */}
                                <div className="pis-audio-section">
                                  <span className="pis-section-label">Listen</span>
                                  {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                                  <audio
                                    controls
                                    src={getAudioUrl(script.id)}
                                    className="pis-audio-player"
                                    preload="none"
                                  />
                                </div>

                                {/* Script text */}
                                <div className="pis-text-section">
                                  <span className="pis-section-label">Read Script</span>
                                  <div className="pis-script-text">{script.approved_script}</div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};

export default PatientImaginalScripts;
