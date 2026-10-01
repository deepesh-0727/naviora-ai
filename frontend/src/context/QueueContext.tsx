import React, { createContext, useContext, useState, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface QueueData {
  position: number;
  estimatedWait: number;
  status: string;
  doctorName?: string;
}

interface QueueContextType {
  queueData: QueueData | null;
  setQueueData: (data: QueueData | null) => void;
}

const QueueContext = createContext<QueueContextType | undefined>(undefined);

export const QueueProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [queueData, setQueueData] = useState<QueueData | null>(null);
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    if (lastMessage && lastMessage.type === 'queue_update') {
      setQueueData({
        position: lastMessage.position,
        estimatedWait: lastMessage.estimated_wait,
        status: lastMessage.status || 'checked_in',
        doctorName: lastMessage.doctor_name
      });
    }
  }, [lastMessage]);

  return (
    <QueueContext.Provider value={{ queueData, setQueueData }}>
      {children}
    </QueueContext.Provider>
  );
};

export const useQueue = () => {
  const context = useContext(QueueContext);
  if (context === undefined) {
    throw new Error('useQueue must be used within a QueueProvider');
  }
  return context;
};
