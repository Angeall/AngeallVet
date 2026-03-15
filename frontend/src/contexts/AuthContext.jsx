import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../services/supabase';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing Supabase session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        // Fetch the local user profile from our backend
        authAPI.me()
          .then((res) => setUser(res.data))
          .catch((err) => {
            console.warn('Session exists but /auth/me failed:', err.response?.data?.detail || err.message);
            // Only sign out if the token is truly invalid (expired, malformed).
            // A missing local profile (auto-provisioning failure) should not
            // destroy the Supabase session – the user can retry via login.
            if (err.response?.status === 401) {
              supabase.auth.signOut();
            }
          })
          .finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    });

    // Listen for auth state changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_OUT') {
          setUser(null);
        } else if (event === 'TOKEN_REFRESHED' && session) {
          // Session refreshed automatically by Supabase
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const login = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      throw new Error(error.message);
    }

    // Fetch local user profile from our backend.
    // The backend auto-provisions the profile on first login, which may
    // need a moment, so we retry once after a short delay if it fails.
    let profileRes;
    try {
      profileRes = await authAPI.me();
    } catch (firstErr) {
      // Wait briefly then retry – gives auto-provisioning time to complete
      await new Promise((r) => setTimeout(r, 1000));
      try {
        profileRes = await authAPI.me();
      } catch (secondErr) {
        // Don't destroy the Supabase session – let the user retry or
        // see a meaningful error instead of a silent logout loop.
        throw new Error(
          secondErr.response?.data?.detail ||
            'Impossible de charger votre profil. Vérifiez la configuration du serveur.'
        );
      }
    }

    setUser(profileRes.data);
    return profileRes.data;
  };

  const logout = async () => {
    await supabase.auth.signOut();
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
