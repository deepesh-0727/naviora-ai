import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function AuditLog() { return <AdminDataScreen title="Audit log" endpoint="/api/v1/admin/audit?limit=100" description="Persisted access and system audit events" />; }
