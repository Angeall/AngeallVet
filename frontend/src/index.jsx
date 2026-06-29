import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { queryClient, persister, CACHE_VERSION } from './services/queryClient';
import { registerOfflineMutations } from './services/mutations';
import './styles/index.css';

// Enregistre les fonctions de mutation avant tout rendu, pour que les écritures
// mises en file d'attente hors ligne puissent reprendre après un rechargement.
registerOfflineMutations();

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{ persister, maxAge: 7 * 24 * 60 * 60 * 1000, buster: CACHE_VERSION }}
        onSuccess={() => { queryClient.resumePausedMutations(); }}
      >
        <AuthProvider>
          <App />
        </AuthProvider>
      </PersistQueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
