import React, { createContext, useContext, useState, useEffect } from 'react';
import { pb, USERS_COLLECTION } from '../services/pocketbase';
import { authAPI, setAppToken } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Exchange the current PocketBase session for an application JWT + profile.
  const establishSession = async () => {
    const { data } = await authAPI.session(pb.authStore.token);
    setAppToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  useEffect(() => {
    let active = true;
    // Restore the session on load if PocketBase still has a valid token.
    if (pb.authStore.isValid) {
      establishSession()
        .catch((err) => {
          console.warn(
            'Session PocketBase non rétablie:',
            err?.response?.data?.detail || err.message
          );
          setAppToken(null);
          pb.authStore.clear();
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    } else {
      setLoading(false);
    }
    return () => {
      active = false;
    };
  }, []);

  const login = async (email, password) => {
    // 1. Authenticate directly against the tenant's PocketBase instance.
    try {
      await pb.collection(USERS_COLLECTION).authWithPassword(email, password);
    } catch (err) {
      throw new Error('Email ou mot de passe incorrect');
    }
    // 2. Exchange the PocketBase token for an application JWT + load the profile.
    try {
      return await establishSession();
    } catch (err) {
      pb.authStore.clear();
      setAppToken(null);
      throw new Error(
        err?.response?.data?.detail ||
          'Connexion impossible. Vérifiez la configuration du serveur.'
      );
    }
  };

  const logout = async () => {
    pb.authStore.clear();
    setAppToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
