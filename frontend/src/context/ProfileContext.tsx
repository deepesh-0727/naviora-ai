import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface UserProfile {
  id: string;
  name: string;
  role: 'patient' | 'doctor' | 'staff';
}

interface ProfileContextType {
  profile: UserProfile | null;
  setProfile: (profile: UserProfile | null) => void;
}

const ProfileContext = createContext<ProfileContextType | undefined>(undefined);

export const ProfileProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    AsyncStorage.getItem('profile').then(value => {
      if (value) setProfile(JSON.parse(value));
    });
  }, []);

  const updateProfile = (value: UserProfile | null) => {
    setProfile(value);
    if (value) AsyncStorage.setItem('profile', JSON.stringify(value));
    else AsyncStorage.removeItem('profile');
  };

  return (
    <ProfileContext.Provider value={{ profile, setProfile: updateProfile }}>
      {children}
    </ProfileContext.Provider>
  );
};

export const useProfile = () => {
  const context = useContext(ProfileContext);
  if (!context) throw new Error('useProfile must be used within a ProfileProvider');
  return context;
};
