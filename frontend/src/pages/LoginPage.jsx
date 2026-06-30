import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success('Connexion reussie');
      navigate('/');
    } catch (err) {
      toast.error(err.message || 'Email ou mot de passe incorrect');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-visual">
        <div className="login-visual-content">
          <div className="login-visual-icon">
            <img src="/logo.png" alt="AngeallVet" onError={(e) => { const b = e.currentTarget.closest('.login-visual-icon'); if (b) b.style.display = 'none'; }} />
          </div>
          <h2>AngeallVet</h2>
          <p>Votre solution complete de gestion de clinique veterinaire. Patients, agenda, dossiers medicaux, stocks et facturation en un seul endroit.</p>
        </div>
      </div>

      <div className="login-form-side">
        <div className="login-card">
          <div className="login-card-logo">
            <div className="sidebar-logo-icon" style={{ width: 36, height: 36 }}>
              <img src="/logo.png" alt="AngeallVet" onError={(e) => { const b = e.currentTarget.closest('.sidebar-logo-icon'); if (b) b.style.display = 'none'; }} />
            </div>
          </div>
          <h1 className="login-title">Bienvenue</h1>
          <p className="login-subtitle">Connectez-vous a votre espace AngeallVet</p>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Adresse email</label>
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nom@clinique.fr"
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Mot de passe</label>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Votre mot de passe"
                required
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ width: '100%', marginTop: '8px' }}
              disabled={loading}
            >
              {loading ? 'Connexion...' : 'Se connecter'}
            </button>
          </form>

          <div className="login-demo">
            <div className="login-demo-label">Identifiants de demo</div>
            <div className="login-demo-cred">admin@angeallvet.fr / admin123</div>
          </div>
        </div>
      </div>
    </div>
  );
}
