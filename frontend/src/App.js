import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

const API_BASE = '';  // Uses nginx proxy via REACT_APP_API_URL or relative

const api = axios.create({
  baseURL: window.location.origin.includes('3000') 
    ? 'http://localhost:8080'  // Dev: direct to nginx
    : '',                       // Prod: same origin (served by nginx)
  timeout: 10000,
});

// ============ ICONS ============
const Icon = ({ name, size = 20 }) => {
  const icons = {
    car: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 17H3a2 2 0 01-2-2V9a2 2 0 012-2h3l2-4h8l2 4h3a2 2 0 012 2v6a2 2 0 01-2 2h-2M7 17h10M9 17v2M15 17v2M5 9h14"/></svg>,
    users: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>,
    payment: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>,
    bell: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/></svg>,
    activity: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
    map: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>,
    server: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>,
    check: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>,
    x: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
    loader: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>,
  };
  return icons[name] || null;
};

// ============ STYLES ============
const styles = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    font-family: 'DM Sans', sans-serif;
    background: #070710;
    color: #e8e8f0;
    min-height: 100vh;
  }
  
  :root {
    --accent: #7c3aed;
    --accent-bright: #a855f7;
    --accent-glow: rgba(124, 58, 237, 0.3);
    --green: #10b981;
    --red: #ef4444;
    --yellow: #f59e0b;
    --surface: rgba(255,255,255,0.04);
    --surface-hover: rgba(255,255,255,0.07);
    --border: rgba(255,255,255,0.08);
    --text-dim: rgba(232,232,240,0.5);
    --mono: 'Space Mono', monospace;
  }

  .app { display: flex; height: 100vh; overflow: hidden; }

  /* SIDEBAR */
  .sidebar {
    width: 240px;
    background: rgba(10,10,20,0.9);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    backdrop-filter: blur(20px);
  }
  
  .sidebar-logo {
    padding: 24px 20px;
    border-bottom: 1px solid var(--border);
  }
  
  .logo-text {
    font-family: var(--mono);
    font-size: 20px;
    font-weight: 700;
    background: linear-gradient(135deg, #a855f7, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }
  
  .logo-sub {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 2px;
    font-family: var(--mono);
  }
  
  .sidebar-nav {
    flex: 1;
    padding: 16px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--text-dim);
    font-size: 14px;
    font-weight: 500;
    border: 1px solid transparent;
    background: none;
    width: 100%;
    text-align: left;
  }
  
  .nav-item:hover {
    background: var(--surface);
    color: #e8e8f0;
  }
  
  .nav-item.active {
    background: var(--accent-glow);
    border-color: rgba(124,58,237,0.4);
    color: #a855f7;
  }
  
  .ws-status {
    margin: 12px;
    padding: 10px 14px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface);
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-dim);
    font-family: var(--mono);
  }
  
  .ws-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--red);
    flex-shrink: 0;
    transition: background 0.3s;
  }
  
  .ws-dot.connected { background: var(--green); box-shadow: 0 0 8px var(--green); }

  /* MAIN */
  .main {
    flex: 1;
    overflow-y: auto;
    padding: 32px;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }
  
  .page-header {
    margin-bottom: 28px;
  }
  
  .page-title {
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.5px;
  }
  
  .page-sub {
    color: var(--text-dim);
    font-size: 14px;
    margin-top: 4px;
  }

  /* CARDS */
  .grid { display: grid; gap: 16px; }
  .grid-2 { grid-template-columns: repeat(2, 1fr); }
  .grid-3 { grid-template-columns: repeat(3, 1fr); }
  .grid-4 { grid-template-columns: repeat(4, 1fr); }
  
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    transition: border-color 0.2s;
  }
  
  .card:hover { border-color: rgba(255,255,255,0.14); }
  
  .stat-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .stat-label {
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: var(--mono);
  }
  
  .stat-value {
    font-size: 32px;
    font-weight: 600;
    font-family: var(--mono);
    letter-spacing: -1px;
  }

  /* FORMS */
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 16px;
  }
  
  label {
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: var(--mono);
  }
  
  input, select {
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: #e8e8f0;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    padding: 10px 14px;
    outline: none;
    transition: border-color 0.2s;
    width: 100%;
  }
  
  input:focus, select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }
  
  select option { background: #13131f; }

  /* BUTTONS */
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    border: none;
    font-family: 'DM Sans', sans-serif;
  }
  
  .btn-primary {
    background: var(--accent);
    color: white;
  }
  
  .btn-primary:hover { background: #6d28d9; transform: translateY(-1px); }
  .btn-primary:active { transform: translateY(0); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  
  .btn-ghost {
    background: var(--surface);
    color: #e8e8f0;
    border: 1px solid var(--border);
  }
  
  .btn-ghost:hover { background: var(--surface-hover); }
  
  .btn-sm { padding: 6px 14px; font-size: 13px; }
  .btn-full { width: 100%; }

  /* TABLE */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  
  th {
    text-align: left;
    padding: 10px 14px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    font-family: var(--mono);
    border-bottom: 1px solid var(--border);
    font-weight: 400;
  }
  
  td {
    padding: 12px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    vertical-align: middle;
  }
  
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.02); }

  /* BADGES */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 500;
    font-family: var(--mono);
  }
  
  .badge-green { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.25); }
  .badge-red { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }
  .badge-yellow { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.25); }
  .badge-purple { background: rgba(124,58,237,0.15); color: #a855f7; border: 1px solid rgba(124,58,237,0.25); }
  .badge-gray { background: rgba(255,255,255,0.07); color: var(--text-dim); border: 1px solid var(--border); }

  /* NOTIFICATIONS */
  .notifications-panel {
    position: fixed;
    top: 20px;
    right: 20px;
    width: 320px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 1000;
    pointer-events: none;
  }
  
  .notification-toast {
    background: rgba(20,20,35,0.95);
    border: 1px solid rgba(124,58,237,0.4);
    border-radius: 10px;
    padding: 14px 16px;
    backdrop-filter: blur(20px);
    pointer-events: all;
    animation: slideIn 0.3s ease;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
  }
  
  @keyframes slideIn {
    from { transform: translateX(120%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  .toast-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  
  .toast-type { font-size: 11px; color: var(--accent-bright); font-family: var(--mono); text-transform: uppercase; letter-spacing: 1px; }
  .toast-close { background: none; border: none; color: var(--text-dim); cursor: pointer; padding: 2px; }
  .toast-msg { font-size: 13px; color: #e8e8f0; line-height: 1.4; }
  .toast-time { font-size: 11px; color: var(--text-dim); margin-top: 6px; font-family: var(--mono); }

  /* HEALTH MONITOR */
  .health-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  
  .health-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .health-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  
  .health-info { flex: 1; }
  .health-name { font-size: 13px; font-weight: 500; }
  .health-status { font-size: 11px; color: var(--text-dim); font-family: var(--mono); margin-top: 2px; }

  /* RIDE LOG */
  .ride-log {
    max-height: 200px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    scrollbar-width: thin;
  }
  
  .log-entry {
    padding: 8px 12px;
    background: rgba(255,255,255,0.03);
    border-radius: 6px;
    border-left: 2px solid var(--accent);
    font-size: 12px;
    font-family: var(--mono);
    color: var(--text-dim);
  }
  
  .log-time { color: var(--accent-bright); }
  
  /* SECTION TITLE */
  .section-title {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 14px;
    color: #e8e8f0;
    letter-spacing: -0.2px;
  }

  /* TABS */
  .tabs {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
  }
  
  .tab {
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-dim);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    background: none;
    border-top: none;
    border-left: none;
    border-right: none;
    font-family: 'DM Sans', sans-serif;
    transition: all 0.15s;
  }
  
  .tab:hover { color: #e8e8f0; }
  .tab.active { color: var(--accent-bright); border-bottom-color: var(--accent-bright); }
  
  /* ALERT BOX */
  .alert {
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    margin-top: 12px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }
  
  .alert-success { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); color: #10b981; }
  .alert-error { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); color: #ef4444; }

  /* SPIN ANIMATION */
  .spin { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  
  .mono { font-family: var(--mono); }
  .text-dim { color: var(--text-dim); }
  .text-green { color: var(--green); }
  .text-red { color: var(--red); }
  .text-accent { color: var(--accent-bright); }
  .mt-4 { margin-top: 16px; }
  .mb-4 { margin-bottom: 16px; }
  .gap-2 { gap: 8px; }
  .flex { display: flex; }
  .flex-between { display: flex; justify-content: space-between; align-items: center; }
  .items-center { align-items: center; }
`;

// ============ STATUS BADGE HELPER ============
const StatusBadge = ({ status }) => {
  const map = {
    matched: 'badge-purple', active: 'badge-yellow', paid: 'badge-green',
    completed: 'badge-green', pending: 'badge-yellow', cancelled: 'badge-red',
    available: 'badge-green', unavailable: 'badge-gray',
  };
  return <span className={`badge ${map[status] || 'badge-gray'}`}>{status}</span>;
};

// ============ RIDE PANEL ============
function RidePanel({ onRideRequested }) {
  const [riderId, setRiderId] = useState('1');
  const [pickup, setPickup] = useState('');
  const [dropoff, setDropoff] = useState('');
  const [rideType, setRideType] = useState('standard');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const requestRide = async () => {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.post('/ride/request', {
        riderId: parseInt(riderId),
        pickup: pickup || 'Current Location',
        dropoff: dropoff || 'Destination',
        ride_type: rideType
      });
      setResult(res.data);
      onRideRequested?.(res.data);
    } catch (e) {
      const status = e.response?.status;
      const detail = e.response?.data?.detail || e.message || 'Failed to request ride';
      if (status === 503) {
        setError('🚫 ' + detail); // No drivers available
      } else {
        setError(detail);
      }
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="grid grid-2" style={{ gap: 16, marginBottom: 20 }}>
        <div className="form-group">
          <label>Rider ID</label>
          <input type="number" value={riderId} onChange={e => setRiderId(e.target.value)} placeholder="1" />
        </div>
        <div className="form-group">
          <label>Ride Type</label>
          <select value={rideType} onChange={e => setRideType(e.target.value)}>
            <option value="standard">Standard — $15 base</option>
            <option value="premium">Premium — $25 base</option>
            <option value="xl">XL — $35 base</option>
            <option value="economy">Economy — $10 base</option>
          </select>
        </div>
        <div className="form-group">
          <label>Pickup Location</label>
          <input value={pickup} onChange={e => setPickup(e.target.value)} placeholder="Current Location" />
        </div>
        <div className="form-group">
          <label>Drop-off Location</label>
          <input value={dropoff} onChange={e => setDropoff(e.target.value)} placeholder="Destination" />
        </div>
      </div>

      <button className="btn btn-primary btn-full" onClick={requestRide} disabled={loading}>
        {loading ? <><span className="spin"><Icon name="loader" size={16} /></span> Matching...</> : <><Icon name="car" size={16} /> Request Ride</>}
      </button>

      {result && (
        <div className="alert alert-success">
          <Icon name="check" size={16} />
          <div>
            <strong>Ride Matched!</strong> — ID: <code className="mono">{result.ride_id}</code><br/>
            Driver: {result.driver?.name || 'Assigned'} · Est. ${result.price?.toFixed(2)} · {result.estimated_arrival}
          </div>
        </div>
      )}
      {error && (
        <div className="alert alert-error">
          <Icon name="x" size={16} />
          {error}
        </div>
      )}
    </div>
  );
}

// ============ PAYMENT PANEL ============
function PaymentPanel() {
  const [rideId, setRideId] = useState('');
  const [userId, setUserId] = useState('1');
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('card');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [payments, setPayments] = useState([]);

  const loadPayments = async () => {
    try {
      const res = await api.get('/payments');
      setPayments(res.data.payments || []);
    } catch (e) {}
  };

  useEffect(() => { loadPayments(); }, []);

  const makePayment = async () => {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.post('/payments', {
        rideId, userId: parseInt(userId), amount: parseFloat(amount), payment_method: method
      });
      setResult(res.data);
      loadPayments();
    } catch (e) {
      const status = e.response?.status;
      const detail = e.response?.data?.detail || e.message;
      if (status === 403) {
        setError('🔒 Unauthorized: ' + detail);
      } else if (status === 400) {
        setError('⚠️ ' + detail);
      } else if (status === 404) {
        setError('🔍 Ride not found. Check the Ride ID.');
      } else if (status === 503) {
        setError('🚫 ' + detail);
      } else {
        setError(detail || 'Payment failed. Please try again.');
      }
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="grid grid-2" style={{ gap: 16, marginBottom: 20 }}>
        <div className="form-group">
          <label>Ride ID</label>
          <input value={rideId} onChange={e => setRideId(e.target.value)} placeholder="ride-abc123" />
        </div>
        <div className="form-group">
          <label>User ID</label>
          <input type="number" value={userId} onChange={e => setUserId(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Amount ($)</label>
          <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} placeholder="25.00" />
        </div>
        <div className="form-group">
          <label>Payment Method</label>
          <select value={method} onChange={e => setMethod(e.target.value)}>
            <option value="card">Credit Card</option>
            <option value="wallet">Digital Wallet</option>
            <option value="cash">Cash</option>
          </select>
        </div>
      </div>

      <button className="btn btn-primary" onClick={makePayment} disabled={loading || !rideId || !amount}>
        {loading ? <><span className="spin"><Icon name="loader" size={16}/></span> Processing...</> : <><Icon name="payment" size={16} /> Make Payment</>}
      </button>

      {result && <div className="alert alert-success"><Icon name="check" size={16} /><div>Payment <code className="mono">{result.transaction_id}</code> — ${result.amount?.toFixed(2)} completed!</div></div>}
      {error && <div className="alert alert-error"><Icon name="x" size={16} />{error}</div>}

      {payments.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <p className="section-title">Recent Payments</p>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead><tr><th>Transaction</th><th>Ride ID</th><th>User</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
              <tbody>
                {payments.slice(0, 8).map(p => (
                  <tr key={p.id}>
                    <td className="mono" style={{ fontSize: 12 }}>{p.transaction_id}</td>
                    <td className="mono text-dim" style={{ fontSize: 12 }}>{p.ride_id?.slice(0, 16)}...</td>
                    <td>{p.user_id}</td>
                    <td className="mono text-green">${parseFloat(p.amount).toFixed(2)}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td className="text-dim" style={{ fontSize: 12 }}>{new Date(p.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ============ USERS / DRIVERS PANEL ============
function UsersPanel() {
  const [tab, setTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === 'users') {
        const res = await api.get('/users');
        setUsers(res.data.users || []);
      } else {
        const res = await api.get('/drivers');
        setDrivers(res.data.drivers || []);
      }
    } catch (e) {}
    setLoading(false);
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="tabs">
        <button className={`tab ${tab === 'users' ? 'active' : ''}`} onClick={() => setTab('users')}>Riders</button>
        <button className={`tab ${tab === 'drivers' ? 'active' : ''}`} onClick={() => setTab('drivers')}>Drivers</button>
      </div>

      <div className="flex-between mb-4">
        <span className="text-dim" style={{ fontSize: 13 }}>{tab === 'users' ? users.length : drivers.length} records</span>
        <button className="btn btn-ghost btn-sm" onClick={load}>{loading ? <span className="spin"><Icon name="loader" size={14}/></span> : 'Refresh'}</button>
      </div>

      {tab === 'users' ? (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Joined</th></tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td className="mono text-accent">#{u.id}</td>
                  <td style={{ fontWeight: 500 }}>{u.name}</td>
                  <td className="text-dim">{u.email}</td>
                  <td className="mono text-dim" style={{ fontSize: 12 }}>{u.phone}</td>
                  <td className="text-dim" style={{ fontSize: 12 }}>{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Name</th><th>Vehicle</th><th>Rating</th><th>Status</th><th>Rides</th></tr></thead>
            <tbody>
              {drivers.map(d => (
                <tr key={d._id}>
                  <td style={{ fontWeight: 500 }}>{d.name}</td>
                  <td className="text-dim" style={{ fontSize: 12 }}>{d.vehicle}</td>
                  <td className="text-accent mono">★ {d.rating?.toFixed(1)}</td>
                  <td><StatusBadge status={d.available ? 'available' : 'unavailable'} /></td>
                  <td className="mono">{d.total_rides}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============ RIDE HISTORY PANEL ============
function RideHistoryPanel() {
  const [rides, setRides] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get('/rides');
      setRides(res.data.rides || []);
    } catch (e) {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex-between mb-4">
        <span className="text-dim" style={{ fontSize: 13 }}>{rides.length} rides in Redis</span>
        <button className="btn btn-ghost btn-sm" onClick={load}>{loading ? 'Loading...' : 'Refresh'}</button>
      </div>

      {rides.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-dim)' }}>
          <Icon name="car" size={32} />
          <p style={{ marginTop: 12, fontSize: 14 }}>No rides yet. Request a ride to get started!</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Ride ID</th><th>Rider</th><th>Driver</th><th>Type</th><th>Price</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {rides.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).map(r => (
                <tr key={r.ride_id}>
                  <td className="mono text-accent" style={{ fontSize: 12 }}>{r.ride_id}</td>
                  <td>User #{r.rider_id}</td>
                  <td className="text-dim" style={{ fontSize: 12 }}>{r.driver_name || r.driver_id?.slice(0, 10)}</td>
                  <td><span className="badge badge-gray">{r.ride_type}</span></td>
                  <td className="mono text-green">${parseFloat(r.price || 0).toFixed(2)}</td>
                  <td><StatusBadge status={r.status} /></td>
                  <td className="text-dim" style={{ fontSize: 12 }}>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============ HEALTH MONITOR ============
function HealthMonitor() {
  const services = [
    { name: 'User Service', path: '/health/users', db: 'MySQL' },
    { name: 'Driver Service', path: '/health/drivers', db: 'MongoDB' },
    { name: 'Ride Matching', path: '/health/rides', db: 'Redis' },
    { name: 'Payment Service', path: '/health/payments', db: 'MySQL' },
    { name: 'Notifications', path: '/health/notifications', db: 'MongoDB' },
    { name: 'Pricing Service', path: '/health/pricing', db: 'Redis' },
  ];

  const [statuses, setStatuses] = useState({});
  const [checking, setChecking] = useState(false);

  const checkAll = async () => {
    setChecking(true);
    const results = {};
    await Promise.all(services.map(async (s) => {
      try {
        const start = Date.now();
        await api.get(s.path, { timeout: 4000 });
        results[s.name] = { ok: true, latency: Date.now() - start };
      } catch {
        results[s.name] = { ok: false };
      }
    }));
    setStatuses(results);
    setChecking(false);
  };

  useEffect(() => { checkAll(); }, []);

  return (
    <div>
      <div className="flex-between mb-4">
        <span className="text-dim" style={{ fontSize: 13 }}>
          {Object.values(statuses).filter(s => s.ok).length}/{services.length} services healthy
        </span>
        <button className="btn btn-ghost btn-sm" onClick={checkAll} disabled={checking}>
          {checking ? <span className="spin"><Icon name="loader" size={14}/></span> : 'Check All'}
        </button>
      </div>
      <div className="health-grid">
        {services.map(s => {
          const st = statuses[s.name];
          return (
            <div className="health-item" key={s.name}>
              <div className="health-dot" style={{
                background: st ? (st.ok ? 'var(--green)' : 'var(--red)') : 'var(--text-dim)',
                boxShadow: st?.ok ? '0 0 8px var(--green)' : 'none'
              }}/>
              <div className="health-info">
                <div className="health-name">{s.name}</div>
                <div className="health-status">
                  {st ? (st.ok ? `Online · ${st.latency}ms · ${s.db}` : `Offline · ${s.db}`) : `Checking · ${s.db}`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============ MAIN APP ============
export default function App() {
  const [page, setPage] = useState('dashboard');
  const [wsConnected, setWsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [recentRides, setRecentRides] = useState([]);
  const wsRef = useRef(null);

  // WebSocket setup
  useEffect(() => {
    const connect = () => {
      const wsHost = window.location.hostname;
      const wsPort = window.location.port === '3000' ? '8080' : window.location.port;
      const wsUrl = `ws://${wsHost}:${wsPort}/ws`;
      
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => {
          setWsConnected(false);
          setTimeout(connect, 3000);
        };
        ws.onerror = () => setWsConnected(false);
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (data.type === 'notification') {
              const toast = { ...data, id: Date.now() };
              setNotifications(prev => [toast, ...prev].slice(0, 5));
            }
          } catch {}
        };
        
        const ping = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
        
        return () => clearInterval(ping);
      } catch (e) {}
    };
    
    connect();
    return () => wsRef.current?.close();
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'activity' },
    { id: 'request', label: 'Request Ride', icon: 'car' },
    { id: 'payment', label: 'Payment', icon: 'payment' },
    { id: 'users', label: 'Users & Drivers', icon: 'users' },
    { id: 'history', label: 'Ride History', icon: 'map' },
    { id: 'health', label: 'Service Health', icon: 'server' },
  ];

  const dismissNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const handleRideRequested = (ride) => {
    setRecentRides(prev => [ride, ...prev].slice(0, 10));
  };

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return (
          <div>
            <div className="page-header">
              <h1 className="page-title">Dashboard</h1>
              <p className="page-sub">Distributed Microservices Ride Platform — Real-time Overview</p>
            </div>
            
            <div className="grid grid-4" style={{ marginBottom: 24 }}>
              {[
                { label: 'Architecture', value: 'gRPC + REST', accent: true },
                { label: 'Databases', value: '4 Types' },
                { label: 'Services', value: '6 Active' },
                { label: 'WebSocket', value: wsConnected ? 'Live ●' : 'Offline ○' },
              ].map(s => (
                <div className="card stat-card" key={s.label}>
                  <div className="stat-label">{s.label}</div>
                  <div className="stat-value mono" style={{ fontSize: 20, color: s.accent ? 'var(--accent-bright)' : wsConnected && s.label === 'WebSocket' ? 'var(--green)' : '#e8e8f0' }}>
                    {s.value}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="grid grid-2" style={{ marginBottom: 24 }}>
              <div className="card">
                <p className="section-title">Quick Ride Request</p>
                <RidePanel onRideRequested={handleRideRequested} />
              </div>
              <div className="card">
                <p className="section-title">Recent Activity</p>
                {recentRides.length === 0 ? (
                  <p className="text-dim" style={{ fontSize: 13 }}>No rides yet in this session.</p>
                ) : (
                  <div className="ride-log">
                    {recentRides.map((r, i) => (
                      <div className="log-entry" key={i}>
                        <span className="log-time">{new Date().toLocaleTimeString()}</span> Ride <span style={{ color: '#e8e8f0' }}>{r.ride_id}</span> — ${r.price?.toFixed(2)} · {r.driver?.name}
                      </div>
                    ))}
                  </div>
                )}
                
                <div style={{ marginTop: 20 }}>
                  <p className="section-title">Notification Feed</p>
                  {notifications.length === 0 ? (
                    <p className="text-dim" style={{ fontSize: 13 }}>Waiting for WebSocket events...</p>
                  ) : (
                    <div className="ride-log">
                      {notifications.map(n => (
                        <div className="log-entry" key={n.id}>
                          <span className="log-time">[{n.notification_type}]</span> {n.message}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="card">
              <p className="section-title">Service Health</p>
              <HealthMonitor />
            </div>
          </div>
        );
      case 'request':
        return (
          <div>
            <div className="page-header">
              <h1 className="page-title">Request a Ride</h1>
              <p className="page-sub">POST /ride/request → NGINX → Ride Matching Service → gRPC → Driver + Pricing</p>
            </div>
            <div className="card"><RidePanel onRideRequested={handleRideRequested} /></div>
          </div>
        );
      case 'payment':
        return (
          <div>
            <div className="page-header">
              <h1 className="page-title">Payment</h1>
              <p className="page-sub">POST /payments → NGINX → Payment Service → gRPC → Ride Validation → MySQL</p>
            </div>
            <div className="card"><PaymentPanel /></div>
          </div>
        );
      case 'users':
        return (
          <div>
            <div className="page-header">
              <h1 className="page-title">Users & Drivers</h1>
              <p className="page-sub">GET /users (MySQL) · GET /drivers (MongoDB)</p>
            </div>
            <div className="card"><UsersPanel /></div>
          </div>
        );
      case 'history':
        return (
          <div>
            <div className="page-header">
              <h1 className="page-title">Ride History</h1>
              <p className="page-sub">All rides stored in Redis — GET /rides</p>
            </div>
            <div className="card"><RideHistoryPanel /></div>
          </div>
        );
      case 'health':
        return (
          <div>
            <div className="page-header">
              <h1 className="page-title">Service Health Monitor</h1>
              <p className="page-sub">Real-time health checks via NGINX API Gateway</p>
            </div>
            <div className="card"><HealthMonitor /></div>
            
            <div className="card mt-4">
              <p className="section-title">Architecture Map</p>
              <div className="grid grid-3" style={{ gap: 12 }}>
                {[
                  { name: 'User Service', db: 'MySQL :3306', port: ':8001', color: '#3b82f6' },
                  { name: 'Driver Service', db: 'MongoDB :27017', port: ':8002 + gRPC :50052', color: '#8b5cf6' },
                  { name: 'Ride Matching', db: 'Redis :6379', port: ':8003 + gRPC :50051', color: '#ec4899' },
                  { name: 'Payment Service', db: 'MySQL :3306', port: ':8004', color: '#10b981' },
                  { name: 'Notification', db: 'MongoDB :27017', port: ':8005 + WS', color: '#f59e0b' },
                  { name: 'Pricing Service', db: 'Redis :6379', port: ':8006 + gRPC :50053', color: '#ef4444' },
                ].map(s => (
                  <div key={s.name} style={{ padding: '14px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, borderLeft: `3px solid ${s.color}` }}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>{s.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{s.port}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginTop: 2 }}>{s.db}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <>
      <style>{styles}</style>
      <div className="app">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-logo">
            <div className="logo-text">RideBook</div>
            <div className="logo-sub">Microservices Platform</div>
          </div>
          <nav className="sidebar-nav">
            {navItems.map(item => (
              <button
                key={item.id}
                className={`nav-item ${page === item.id ? 'active' : ''}`}
                onClick={() => setPage(item.id)}
              >
                <Icon name={item.icon} size={16} />
                {item.label}
              </button>
            ))}
          </nav>
          <div className="ws-status">
            <div className={`ws-dot ${wsConnected ? 'connected' : ''}`} />
            {wsConnected ? 'WS Live' : 'WS Offline'}
          </div>
        </aside>

        {/* Main content */}
        <main className="main">{renderPage()}</main>
      </div>

      {/* Toast notifications */}
      <div className="notifications-panel">
        {notifications.map(n => (
          <div className="notification-toast" key={n.id}>
            <div className="toast-header">
              <span className="toast-type">{n.notification_type}</span>
              <button className="toast-close" onClick={() => dismissNotification(n.id)}><Icon name="x" size={14} /></button>
            </div>
            <div className="toast-msg">{n.message}</div>
            <div className="toast-time">{new Date(n.timestamp).toLocaleTimeString()}</div>
          </div>
        ))}
      </div>
    </>
  );
}
