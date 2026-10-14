import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function Analytics() { return <AdminDataScreen title="Analytics" endpoint="/api/v1/admin/analytics/flow" description="Appointment flow aggregated from persisted records" />; }
