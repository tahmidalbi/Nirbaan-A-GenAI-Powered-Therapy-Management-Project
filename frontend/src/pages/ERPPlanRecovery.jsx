import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { listERPItems, createERPItem, updateERPItem, deleteERPItem } from '../api/erp.api';
import '../dashboards/PatientDashboard.css';
import './ERPPlanRecovery.css';

/* ─── helpers ─── */
const emptyForm = () => ({
  obsession: '',
  compulsions: [''],
  suds: '',
});

const ERPPlanRecovery = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const [items, setItems]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');

  /* form state */
  const [showForm, setShowForm]   = useState(false);
  const [editingId, setEditingId] = useState(null); // null = new item
  const [form, setForm]           = useState(emptyForm());
  const [saving, setSaving]       = useState(false);
  const [formError, setFormError] = useState('');

  /* ─── load items ─── */
  const loadItems = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const { data } = await listERPItems();
      setItems(data);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Failed to load items.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadItems(); }, [loadItems]);

  /* ─── open form for NEW item ─── */
  const openNewForm = () => {
    setEditingId(null);
    setForm(emptyForm());
    setFormError('');
    setShowForm(true);
  };

  /* ─── open form to EDIT an existing item ─── */
  const openEditForm = (item) => {
    setEditingId(item.id);
    setForm({
      obsession: item.obsession,
      compulsions: item.compulsions.length > 0 ? [...item.compulsions] : [''],
      suds: item.suds !== null && item.suds !== undefined ? String(item.suds) : '',
    });
    setFormError('');
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm());
    setFormError('');
  };

  /* ─── compulsion helpers ─── */
  const updateCompulsion = (idx, value) => {
    const updated = [...form.compulsions];
    updated[idx] = value;
    setForm((f) => ({ ...f, compulsions: updated }));
  };

  const addCompulsion = () =>
    setForm((f) => ({ ...f, compulsions: [...f.compulsions, ''] }));

  const removeCompulsion = (idx) => {
    if (form.compulsions.length === 1) return; // keep at least one
    const updated = form.compulsions.filter((_, i) => i !== idx);
    setForm((f) => ({ ...f, compulsions: updated }));
  };

  /* ─── submit ─── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!form.obsession.trim()) {
      setFormError('Please describe the obsession.');
      return;
    }

    // filter out blank compulsions
    const compulsions = form.compulsions.map((c) => c.trim()).filter(Boolean);

    const payload = {
      obsession: form.obsession.trim(),
      compulsions,
      suds: form.suds !== '' ? parseInt(form.suds, 10) : null,
    };

    try {
      setSaving(true);
      if (editingId !== null) {
        await updateERPItem(editingId, payload);
      } else {
        await createERPItem(payload);
      }
      await loadItems();
      closeForm();
    } catch (err) {
      setFormError(typeof err === 'string' ? err : 'Could not save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  /* ─── delete ─── */
  const handleDelete = async (itemId) => {
    if (!window.confirm('Delete this ERP item?')) return;
    try {
      await deleteERPItem(itemId);
      setItems((prev) => prev.filter((i) => i.id !== itemId));
      if (editingId === itemId) closeForm();
    } catch (err) {
      alert(typeof err === 'string' ? err : 'Failed to delete item.');
    }
  };

  const handleLogout = () => { logout(); navigate('/'); };

  /* ─── render ─── */
  return (
    <div className="erp-plan-root">
      {/* Background */}
      <div className="pd-bg">
        <div className="pd-bg-grid" />
        <div className="pd-bg-orb pd-bg-orb--1" />
        <div className="pd-bg-orb pd-bg-orb--2" />
      </div>

      {/* Header */}
      <header className="pd-header">
        <div className="pd-header-inner">
          <div className="pd-brand">
            <span className="pd-brand-logo">Nirbaan</span>
            <div className="pd-brand-breadcrumb">
              <span className="pd-brand-sep">&rsaquo;</span>
              <span>Plan Your Recovery</span>
            </div>
          </div>
          <div className="pd-header-actions">
            <button className="pd-back-btn" onClick={() => navigate('/patient/dashboard/erp')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </button>
            <button className="pd-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      <main className="erp-plan-main">
        {/* ── page intro ── */}
        <p className="erp-plan-intro">
          Add each obsession you experience, list the compulsions that follow it, and note
          the exercise your therapist has prescribed for it.
        </p>

        {/* ── global error ── */}
        {error && <div className="erp-alert erp-alert-error">{error}</div>}

        {/* ── items list ── */}
        {loading ? (
          <div className="erp-loading">Loading…</div>
        ) : (
          <div className="erp-items-list">
            {items.length === 0 && (
              <div className="erp-empty-state">
                No items yet. Click <strong>+</strong> to add your first obsession.
              </div>
            )}

            {items.map((item) => (
              <div key={item.id} className="erp-item-card">
                <div className="erp-item-card-main">
                  <h3 className="erp-item-obsession">{item.obsession}</h3>

                  {item.compulsions.length > 0 && (
                    <div className="erp-item-compulsions">
                      <span className="erp-label">Compulsions:</span>
                      <ul>
                        {item.compulsions.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {item.suds !== null && item.suds !== undefined && (
                    <div className="erp-item-suds">
                      <span className="erp-label">Anxiety Rating (SUDS):</span>{' '}
                      <span className="erp-suds-badge">{item.suds} / 100</span>
                    </div>
                  )}
                </div>

                <div className="erp-item-actions">
                  <button
                    className="erp-btn-edit"
                    onClick={() => openEditForm(item)}
                  >
                    Edit
                  </button>
                  <button
                    className="erp-btn-remove"
                    onClick={() => handleDelete(item.id)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── floating add button ── */}
        {!showForm && (
          <button className="erp-fab" onClick={openNewForm} title="Add new obsession item">
            +
          </button>
        )}

        {/* ── form overlay / panel ── */}
        {showForm && (
          <div className="erp-form-overlay" onClick={(e) => e.target === e.currentTarget && closeForm()}>
            <div className="erp-form-panel">
              <div className="erp-form-header">
                <h2>{editingId !== null ? 'Edit Item' : 'New Item'}</h2>
                <button className="erp-form-close" onClick={closeForm}>✕</button>
              </div>

              {formError && <div className="erp-alert erp-alert-error">{formError}</div>}

              <form onSubmit={handleSubmit} className="erp-form">
                {/* obsession */}
                <div className="erp-field">
                  <label className="erp-field-label">Obsession</label>
                  <textarea
                    className="erp-textarea"
                    placeholder="Describe the obsessive thought or fear…"
                    value={form.obsession}
                    onChange={(e) => setForm((f) => ({ ...f, obsession: e.target.value }))}
                    rows={3}
                    required
                  />
                </div>

                {/* compulsions */}
                <div className="erp-field">
                  <label className="erp-field-label">Compulsions</label>
                  {form.compulsions.map((c, idx) => (
                    <div key={idx} className="erp-compulsion-row">
                      <input
                        className="erp-input"
                        type="text"
                        placeholder={`Compulsion ${idx + 1}`}
                        value={c}
                        onChange={(e) => updateCompulsion(idx, e.target.value)}
                      />
                      {form.compulsions.length > 1 && (
                        <button
                          type="button"
                          className="erp-btn-remove-compulsion"
                          onClick={() => removeCompulsion(idx)}
                          title="Remove"
                        >
                          −
                        </button>
                      )}
                    </div>
                  ))}
                  <button type="button" className="erp-btn-add-compulsion" onClick={addCompulsion}>
                    + Add compulsion
                  </button>
                </div>

                {/* suds */}
                <div className="erp-field">
                  <label className="erp-field-label">
                    Anxiety Rating — SUDS (0 = no anxiety, 100 = extreme anxiety)
                  </label>
                  <div className="erp-suds-row">
                    <input
                      className="erp-suds-slider"
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={form.suds === '' ? 50 : form.suds}
                      onChange={(e) => setForm((f) => ({ ...f, suds: e.target.value }))}
                    />
                    <input
                      className="erp-suds-number"
                      type="number"
                      min={0}
                      max={100}
                      placeholder="0–100"
                      value={form.suds}
                      onChange={(e) => {
                        const v = e.target.value;
                        if (v === '' || (Number(v) >= 0 && Number(v) <= 100)) {
                          setForm((f) => ({ ...f, suds: v }));
                        }
                      }}
                    />
                  </div>
                </div>

                {/* actions */}
                <div className="erp-form-actions">
                  <button type="button" className="erp-btn-cancel" onClick={closeForm}>
                    Cancel
                  </button>
                  <button type="submit" className="erp-btn-save" disabled={saving}>
                    {saving ? 'Saving…' : editingId !== null ? 'Save Changes' : 'Add Item'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ERPPlanRecovery;
