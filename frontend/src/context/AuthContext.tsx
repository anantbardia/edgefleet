import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';
import { User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (requiredRole: UserRole) => boolean;
}

const roleWeights: Record<UserRole, number> = {
  viewer: 1,
  operator: 2,
  admin: 3,
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchCurrentUser = async () => {
    try {
      if (localStorage.getItem('edgefleet_access_token')) {
        const u = await api.auth.getMe();
        setUser(u);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
      api.clearTokens();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const login = async (email: string, password: string) => {
    await api.auth.login(email, password);
    const u = await api.auth.getMe();
    setUser(u);
  };

  const logout = () => {
    api.auth.logout();
    setUser(null);
  };

  const hasRole = (requiredRole: UserRole): boolean => {
    if (!user) return false;
    return roleWeights[user.role] >= roleWeights[requiredRole];
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};
