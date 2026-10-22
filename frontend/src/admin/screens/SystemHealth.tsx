import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function SystemHealth() { return <AdminDataScreen title="System health" endpoint="/admin/health/services" description="Live reachability checks for configured services" />; }
