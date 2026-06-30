import React, { createContext, useContext, useState, useEffect } from 'react';
import { pb, USERS_COLLECTION } from '../services/pocketbase';
import { authAPI, setAppToken } from '../services/api';
import { clearOfflineCache } from '../services/queryClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  // Paid modules unlocked for this tenant (UX only — the backend is the real
  // gate, so this list can't unlock anything on its own).
  const [modules, setModules] = useState([]);

  // Exchange the current PocketBase session for an application JWT + profile.
  const establishSession = async () => {
    const { data } = await authAPI.session(pb.authStore.token);
    setAppToken(data.access_token);
    setUser(data.user);
    setModules(data.modules || []);
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
          // Hors ligne / erreur réseau : on garde la session pour la reprise au
          // retour du réseau ; on ne déconnecte que sur un vrai refus serveur.
          if (err?.response) {
            setAppToken(null);
            pb.authStore.clear();
          }
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
    setModules([]);
    // Purge du cache hors ligne : aucune donnée patient ne reste au repos.
    await clearOfflineCache();
  };

  const hasModule = (key) => modules.includes(key);

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout, modules, hasModule }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

// Convenience hook for gating paid features in the UI. Remember this is cosmetic:
// every paid action is also enforced server-side.
export function useModules() {
  const { modules, hasModule } = useAuth();
  return { modules, hasModule };
}
