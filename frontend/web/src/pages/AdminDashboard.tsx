import React, { useState } from 'react';

// Design System Constants (Matches Mobile Theme)
const COLORS = {
  primaryDark: '#0A1628',
  primaryMid: '#1A3A5C',
  primaryBlue: '#0EA5E9',
  accentTeal: '#14B8A6',
  accentAmber: '#F59E0B',
  accentRose: '#EF4444',
  accentPurple: '#8B5CF6',
  textWhite: '#FFFFFF',
  textLight: '#F1F5F9',
  textGray: '#94A3B8',
  glassBg: 'rgba(255, 255, 255, 0.05)',
  glassBorder: 'rgba(255, 255, 255, 0.08)',
};

interface EmergencyItem {
  id: number;
  patient: string;
  location: string;
  severity: number;
  assignedStaff: string;
  timeElapsed: string;
  status: 'DISPATCHED' | 'ARRIVED' | 'RESOLVED';
}

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'emergency' | 'queue' | 'staff' | 'audit'>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [emergencies, setEmergencies] = useState<EmergencyItem[]>([
    { id: 401, patient: 'Rahul Verma', location: 'Wing B, Floor 2 (Orthopedics)', severity: 1, assignedStaff: 'Dr. Drake, Nurse Joy', timeElapsed: '1m 45s', status: 'DISPATCHED' },
    { id: 402, patient: 'Priya Sen', location: 'Main Entrance Lobby', severity: 2, assignedStaff: 'Paramedic Team 1', timeElapsed: '4m 10s', status: 'ARRIVED' }
  ]);

  const SidebarItem = ({ id, label, icon }: { id: any; label: string; icon: string }) => (
    <div
      onClick={() => setActiveTab(id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px 16px',
        margin: '4px 12px',
        borderRadius: '12px',
        cursor: 'pointer',
        backgroundColor: activeTab === id ? COLORS.primaryBlue : 'transparent',
        color: activeTab === id ? '#FFF' : COLORS.textGray,
        transition: 'all 0.2s ease',
      }}
    >
      <span style={{ fontSize: '20px', marginRight: sidebarCollapsed ? '0' : '12px' }}>{icon}</span>
      {!sidebarCollapsed && <span style={{ fontWeight: '600', fontSize: '14px' }}>{label}</span>}
    </div>
  );

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: COLORS.primaryDark, color: COLORS.textWhite, fontFamily: "'Inter', sans-serif" }}>
      
      {/* Sidebar */}
      <aside style={{
        width: sidebarCollapsed ? '80px' : '260px',
        borderRight: `1px solid ${COLORS.glassBorder}`,
        backgroundColor: COLORS.primaryDark,
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.3s ease',
      }}>
        <div style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ minWidth: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, #0EA5E9, #14B8A6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: '#FFF', fontWeight: 'bold' }}>N</span>
          </div>
          {!sidebarCollapsed && <h1 style={{ fontSize: '18px', margin: 0, fontWeight: '800' }}>Naviora AI</h1>}
        </div>

        <nav style={{ flex: 1, marginTop: '20px' }}>
          <SidebarItem id="overview" label="Dashboard" icon="📊" />
          <SidebarItem id="emergency" label="SOS Monitor" icon="🚨" />
          <SidebarItem id="queue" label="Queues" icon="⏱️" />
          <SidebarItem id="staff" label="Staff" icon="🩺" />
          <SidebarItem id="audit" label="Audit Logs" icon="🛡️" />
        </nav>

        <div style={{ padding: '24px', borderTop: `1px solid ${COLORS.glassBorder}` }}>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            style={{ background: 'none', border: 'none', color: COLORS.textGray, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {sidebarCollapsed ? '→' : '← Collapse'}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>

        {/* Topbar */}
        <header style={{ height: '72px', borderBottom: `1px solid ${COLORS.glassBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 32px', backgroundColor: 'rgba(10, 22, 40, 0.8)', backdropFilter: 'blur(10px)', position: 'sticky', top: 0, zIndex: 100 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: COLORS.accentTeal, boxShadow: `0 0 10px ${COLORS.accentTeal}` }} />
            <span style={{ fontWeight: '700', fontSize: '14px' }}>COMMAND CENTER LIVE</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ position: 'relative' }}>
              <span style={{ fontSize: '20px', cursor: 'pointer' }}>🔔</span>
              <div style={{ position: 'absolute', top: '-2px', right: '-2px', width: '8px', height: '8px', backgroundColor: COLORS.accentRose, borderRadius: '50%' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '6px 12px', borderRadius: '20px', backgroundColor: COLORS.glassBg, border: `1px solid ${COLORS.glassBorder}` }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: COLORS.primaryBlue }} />
              <span style={{ fontSize: '14px', fontWeight: '600' }}>Admin Node 01</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div style={{ padding: '32px' }}>

          {/* Metrics Bar */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', marginBottom: '32px' }}>
            <MetricCard title="Total Appointments" value="1,284" trend="+12.5%" color={COLORS.primaryBlue} />
            <MetricCard title="Avg. Wait Time" value="12.4m" trend="-2.1m" color={COLORS.accentTeal} />
            <MetricCard title="Active Emergencies" value={emergencies.length.toString()} trend="Critical" color={COLORS.accentRose} />
            <MetricCard title="System Uptime" value="99.99%" trend="Stable" color={COLORS.accentAmber} />
          </div>

          {/* Grid Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>

            {/* Live SOS Monitor */}
            <section style={{ backgroundColor: COLORS.glassBg, borderRadius: '20px', border: `1px solid ${COLORS.glassBorder}`, padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ fontSize: '20px', margin: 0, fontWeight: '800' }}>Live SOS Dispatch Monitor</h2>
                <button style={{ backgroundColor: COLORS.accentRose, color: '#FFF', border: 'none', padding: '8px 16px', borderRadius: '10px', fontWeight: '700', cursor: 'pointer' }}>
                  + Manual Alert
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {emergencies.map(emg => (
                  <div key={emg.id} style={{ display: 'flex', alignItems: 'center', padding: '16px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: `1px solid ${COLORS.glassBorder}` }}>
                    <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: COLORS.accentRose + '20', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '16px' }}>
                      <span style={{ fontSize: '24px' }}>🚨</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontWeight: '700' }}>{emg.patient}</span>
                        <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '8px', backgroundColor: COLORS.accentRose, color: '#FFF' }}>Level {emg.severity}</span>
                      </div>
                      <div style={{ fontSize: '13px', color: COLORS.textGray, marginTop: '4px' }}>📍 {emg.location} &bull; {emg.assignedStaff}</div>
                    </div>
                    <div style={{ textAlign: 'right', marginRight: '24px' }}>
                      <div style={{ fontSize: '14px', fontWeight: '700', color: COLORS.primaryBlue }}>{emg.timeElapsed}</div>
                      <div style={{ fontSize: '12px', color: COLORS.textGray }}>Elapsed</div>
                    </div>
                    <button style={{ padding: '8px 16px', borderRadius: '8px', border: `1px solid ${COLORS.accentTeal}`, color: COLORS.accentTeal, background: 'none', fontWeight: '700', cursor: 'pointer' }}>
                      Resolve
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {/* Queue Summary */}
            <section style={{ backgroundColor: COLORS.glassBg, borderRadius: '20px', border: `1px solid ${COLORS.glassBorder}`, padding: '24px' }}>
              <h2 style={{ fontSize: '20px', margin: '0 0 24px 0', fontWeight: '800' }}>Department Load</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <QueueProgress label="Cardiology" value={85} color={COLORS.primaryBlue} count="12 Patients" />
                <QueueProgress label="Emergency" value={40} color={COLORS.accentRose} count="4 Patients" />
                <QueueProgress label="Pharmacy" value={65} color={COLORS.accentTeal} count="8 Patients" />
                <QueueProgress label="Radiology" value={20} color={COLORS.accentPurple} count="2 Patients" />
              </div>

              <div style={{ marginTop: '32px', padding: '20px', borderRadius: '16px', background: 'linear-gradient(135deg, #1A3A5C, #0EA5E9)', display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ fontSize: '32px' }}>💡</div>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '15px' }}>AI Orchestration Tip</div>
                  <div style={{ fontSize: '13px', opacity: 0.9 }}>Redistribute 2 nurses from Radiology to Cardiology to reduce wait time by 4.2 mins.</div>
                </div>
              </div>
            </section>

          </div>

          {/* AI Logs */}
          <section style={{ marginTop: '32px', backgroundColor: COLORS.glassBg, borderRadius: '20px', border: `1px solid ${COLORS.glassBorder}`, padding: '24px' }}>
            <h2 style={{ fontSize: '20px', margin: '0 0 20px 0', fontWeight: '800' }}>Autonomous Agent Logs</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
              <LogCard agent="HospitalBrain" action="Appointment Routed" detail="Triaged Patient #102 -> Dr. Sarah (Slot 14:00)" />
              <LogCard agent="NavAgent" action="Path Computed" detail="Patient #992 -> Wing B -> Elevators active" />
              <LogCard agent="SecurityAgent" action="Audit Complete" detail="All PHI records encrypted & verified" />
            </div>
          </section>

        </div>
      </main>
    </div>
  );
};

// UI Components
const MetricCard = ({ title, value, trend, color }: any) => (
  <div style={{ backgroundColor: COLORS.glassBg, border: `1px solid ${COLORS.glassBorder}`, borderRadius: '20px', padding: '24px' }}>
    <div style={{ color: COLORS.textGray, fontSize: '12px', fontWeight: '800', letterSpacing: '1px' }}>{title.toUpperCase()}</div>
    <div style={{ fontSize: '36px', fontWeight: '900', margin: '8px 0', color: '#FFF' }}>{value}</div>
    <div style={{ fontSize: '14px', color, fontWeight: '700' }}>{trend}</div>
  </div>
);

const QueueProgress = ({ label, value, color, count }: any) => (
  <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px' }}>
      <span style={{ fontWeight: '600' }}>{label}</span>
      <span style={{ color: COLORS.textGray }}>{count}</span>
    </div>
    <div style={{ height: '8px', width: '100%', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
      <div style={{ width: `${value}%`, height: '100%', backgroundColor: color, borderRadius: '4px' }} />
    </div>
  </div>
);

const LogCard = ({ agent, action, detail }: any) => (
  <div style={{ padding: '16px', borderRadius: '16px', backgroundColor: 'rgba(255,255,255,0.02)', border: `1px solid ${COLORS.glassBorder}` }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
      <span style={{ fontWeight: '700', color: COLORS.primaryBlue, fontSize: '13px' }}>{agent}</span>
      <span style={{ fontSize: '11px', color: COLORS.textGray }}>JUST NOW</span>
    </div>
    <div style={{ fontWeight: '600', fontSize: '14px' }}>{action}</div>
    <div style={{ fontSize: '12px', color: COLORS.textGray, marginTop: '4px' }}>{detail}</div>
  </div>
);

export default AdminDashboard;
