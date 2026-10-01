import React from 'react';
import { createRoot } from 'react-dom/client';
import AdminDashboard from './pages/AdminDashboard';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AdminDashboard />
  </React.StrictMode>,
);
