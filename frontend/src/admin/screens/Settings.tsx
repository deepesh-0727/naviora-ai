import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function Settings() { return <AdminDataScreen title="System settings" endpoint="/admin/settings" description="Persisted application settings" />; }
