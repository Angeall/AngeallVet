import React, { useState, useRef, useEffect } from 'react';
import { useOnlineStatus, usePendingMutations } from '../../hooks/useOfflineSync';

// Variantes visuelles, calées sur les tokens de couleur de l'app (index.css).
const VARIANTS = {
  offline: { bg: 'var(--warning-light)', fg: '#92400e', border: 'rgba(245,158,11,0.35)', label: 'Hors ligne' },
  syncing: { bg: 'var(--info-light)', fg: '#1e40af', border: 'rgba(59,130,246,0.35)', label: 'Synchronisation…' },
  error: { bg: 'var(--danger-light)', fg: '#b91c1c', border: 'rgba(239,68,68,0.35)', label: 'À vérifier' },
};

const WifiOffIcon = (props) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <line x1="1" y1="1" x2="23" y2="23" /><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" /><path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
    <path d="M10.71 5.05A16 16 0 0 1 22.58 9" /><path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" /><path d="M8.53 16.11a6 6 0 0 1 6.95 0" /><line x1="12" y1="20" x2="12.01" y2="20" />
  </svg>
);

const SyncIcon = (props) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

const AlertIcon = (props) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

export default function OfflineBadge() {
  const online = useOnlineStatus();
  const pending = usePendingMutations();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const pausedCount = pending.filter((m) => m.isPaused).length;
  const failedCount = pending.filter((m) => m.status === 'error').length;

  // En ligne et tout synchronisé : pas de badge, on n'encombre pas l'en-tête.
  let variant = null;
  if (!online) variant = 'offline';
  else if (failedCount > 0) variant = 'error';
  else if (pausedCount > 0) variant = 'syncing';

  // Fermeture au clic en dehors du panneau.
  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  // Le panneau peut rester ouvert le temps de la reconnexion : on le referme
  // tout seul une fois que tout est synchronisé.
  useEffect(() => {
    if (open && !variant) setOpen(false);
  }, [open, variant]);

  if (!variant) return null;

  const v = VARIANTS[variant];
  const count = variant === 'error' ? failedCount : pausedCount;
  const Icon = variant === 'offline' ? WifiOffIcon : variant === 'syncing' ? SyncIcon : AlertIcon;
  const labelText = variant === 'error' ? `${failedCount} à vérifier` : v.label;

  return (
    <div ref={ref} style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
      <style>{'@keyframes ngvSpin{to{transform:rotate(360deg)}}'}</style>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={`État de synchronisation : ${labelText}`}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '7px',
          background: v.bg, color: v.fg, border: `1px solid ${v.border}`,
          borderRadius: 'var(--radius-full)', padding: '6px 11px',
          fontSize: '0.8rem', fontWeight: 500, cursor: 'pointer', lineHeight: 1,
          fontFamily: 'inherit', transition: 'all var(--transition-fast)',
        }}
      >
        <Icon style={variant === 'syncing' ? { animation: 'ngvSpin 1.4s linear infinite' } : undefined} />
        <span>{labelText}</span>
        {variant !== 'error' && count > 0 && (
          <span style={{
            background: v.fg, color: v.bg, borderRadius: 'var(--radius-full)',
            minWidth: '18px', height: '18px', display: 'inline-flex', alignItems: 'center',
            justifyContent: 'center', fontSize: '0.68rem', fontWeight: 600, padding: '0 5px',
          }}>{count}</span>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: '8px',
          width: '340px', maxWidth: 'calc(100vw - 32px)',
          background: 'white', border: '1px solid var(--gray-200)',
          borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
          zIndex: 100, overflow: 'hidden',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 16px', borderBottom: '1px solid var(--gray-100)' }}>
            <span style={{ color: v.fg, display: 'flex' }}><Icon /></span>
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--gray-800)' }}>
                {variant === 'offline' ? 'Mode hors ligne' : variant === 'syncing' ? 'Synchronisation en cours' : 'Synchronisation à vérifier'}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>
                {variant === 'offline'
                  ? 'Vos modifications sont enregistrées sur l’appareil'
                  : variant === 'syncing'
                    ? 'Envoi des modifications au serveur…'
                    : 'Certaines modifications n’ont pas pu être envoyées'}
              </div>
            </div>
          </div>

          <div style={{ maxHeight: '260px', overflowY: 'auto' }}>
            {pending.length === 0 ? (
              <div style={{ padding: '18px 16px', textAlign: 'center', color: 'var(--gray-400)', fontSize: '0.82rem' }}>
                Aucune modification en attente
              </div>
            ) : (
              pending.map((m) => (
                <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 16px', borderBottom: '1px solid var(--gray-50)' }}>
                  <span style={{ color: m.status === 'error' ? 'var(--danger)' : 'var(--warning)', display: 'flex', flexShrink: 0 }}>
                    {m.status === 'error' ? <AlertIcon /> : <SyncIcon />}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.84rem', color: 'var(--gray-800)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.label}</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--gray-400)' }}>
                      {m.status === 'error' ? 'Échec — sera retentée' : 'En attente de synchronisation'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {variant === 'offline' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', padding: '10px 16px', borderTop: '1px solid var(--gray-100)', background: 'var(--gray-25)' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--gray-400)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: '1px' }}>
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span style={{ fontSize: '0.76rem', color: 'var(--gray-500)', lineHeight: 1.5 }}>
                Indisponibles hors ligne : encaissement des paiements et registre des stupéfiants. À nouveau actifs dès la reconnexion.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
