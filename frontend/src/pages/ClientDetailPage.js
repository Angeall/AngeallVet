import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clientsAPI, animalsAPI, billingAPI, communicationsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function ClientDetailPage() {
  const { id } = useParams();
  const [client, setClient] = useState(null);
  const [animals, setAnimals] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [comms, setComms] = useState([]);
  const [tab, setTab] = useState('animals');
  const [showAnimalForm, setShowAnimalForm] = useState(false);
  const [animalForm, setAnimalForm] = useState({
    name: '', species: 'dog', breed: '', sex: 'male',
    date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false,
  });

  const load = async () => {
    try {
      const [cRes, aRes, iRes, commRes] = await Promise.all([
        clientsAPI.get(id),
        animalsAPI.list({ client_id: id }),
        billingAPI.listInvoices({ client_id: id }),
        communicationsAPI.list({ client_id: id }),
      ]);
      setClient(cRes.data);
      setAnimals(aRes.data);
      setInvoices(iRes.data);
      setComms(commRes.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleAnimalSubmit = async (e) => {
    e.preventDefault();
    try {
      await animalsAPI.create({
        ...animalForm,
        client_id: parseInt(id),
        date_of_birth: animalForm.date_of_birth || null,
        microchip_number: animalForm.microchip_number || null,
        tattoo_number: animalForm.tattoo_number || null,
      });
      toast.success('Animal cree');
      setShowAnimalForm(false);
      setAnimalForm({ name: '', species: 'dog', breed: '', sex: 'male', date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false });
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  if (!client) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/clients" className="breadcrumb-link">Clients /</Link>
          <h1 className="page-title">{client.last_name} {client.first_name}</h1>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">P</div>
          <div><div className="stat-value">{animals.length}</div><div className="stat-label">Animaux</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">F</div>
          <div><div className="stat-value">{invoices.length}</div><div className="stat-label">Factures</div></div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${parseFloat(client.account_balance) < 0 ? 'red' : 'green'}`}>EUR</div>
          <div>
            <div className="stat-value">{parseFloat(client.account_balance || 0).toFixed(2)}</div>
            <div className="stat-label">Solde (EUR)</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Coordonnees</h3>
        <div className="form-row" style={{ marginTop: '12px' }}>
          <div><strong>Email:</strong> {client.email || '-'}</div>
          <div><strong>Tel:</strong> {client.phone || '-'}</div>
          <div><strong>Mobile:</strong> {client.mobile || '-'}</div>
        </div>
        <div style={{ marginTop: '8px' }}>
          <strong>Adresse:</strong> {client.address} {client.postal_code} {client.city}
        </div>
      </div>

      <div className="tabs">
        {['animals', 'invoices', 'communications'].map((t) => (
          <button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>
            {t === 'animals' ? 'Animaux' : t === 'invoices' ? 'Factures' : 'Communications'}
          </button>
        ))}
      </div>

      {tab === 'animals' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Animaux</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAnimalForm(!showAnimalForm)}>+ Nouvel animal</button>
          </div>

          {showAnimalForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleAnimalSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Nom *</label>
                    <input className="form-input" value={animalForm.name} onChange={(e) => setAnimalForm({ ...animalForm, name: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Espece *</label>
                    <select className="form-select" value={animalForm.species} onChange={(e) => setAnimalForm({ ...animalForm, species: e.target.value })}>
                      <option value="dog">Chien</option>
                      <option value="cat">Chat</option>
                      <option value="bird">Oiseau</option>
                      <option value="rabbit">Lapin</option>
                      <option value="reptile">Reptile</option>
                      <option value="horse">Cheval</option>
                      <option value="nac">NAC</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Race</label>
                    <input className="form-input" value={animalForm.breed} onChange={(e) => setAnimalForm({ ...animalForm, breed: e.target.value })} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Sexe</label>
                    <select className="form-select" value={animalForm.sex} onChange={(e) => setAnimalForm({ ...animalForm, sex: e.target.value })}>
                      <option value="male">Male</option>
                      <option value="female">Femelle</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Date de naissance</label>
                    <input type="date" className="form-input" value={animalForm.date_of_birth} onChange={(e) => setAnimalForm({ ...animalForm, date_of_birth: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Couleur</label>
                    <input className="form-input" value={animalForm.color} onChange={(e) => setAnimalForm({ ...animalForm, color: e.target.value })} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">N Puce</label>
                    <input className="form-input" value={animalForm.microchip_number} onChange={(e) => setAnimalForm({ ...animalForm, microchip_number: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">N Tatouage</label>
                    <input className="form-input" value={animalForm.tattoo_number} onChange={(e) => setAnimalForm({ ...animalForm, tattoo_number: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input type="checkbox" checked={animalForm.is_neutered} onChange={(e) => setAnimalForm({ ...animalForm, is_neutered: e.target.checked })} />
                      Sterilise
                    </label>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Enregistrer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowAnimalForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <table>
            <thead><tr><th>Nom</th><th>Espece</th><th>Race</th><th>Sexe</th><th>Puce</th></tr></thead>
            <tbody>
              {animals.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/animals/${a.id}`} className="table-link">{a.name}</Link></td>
                  <td>{a.species}</td>
                  <td>{a.breed || '-'}</td>
                  <td>{a.sex}</td>
                  <td>{a.microchip_number || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'invoices' && (
        <div className="card">
          <table>
            <thead><tr><th>N</th><th>Date</th><th>Total</th><th>Statut</th></tr></thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td><Link to={`/invoices/${inv.id}`} className="table-link">{inv.invoice_number}</Link></td>
                  <td>{inv.issue_date}</td>
                  <td>{parseFloat(inv.total).toFixed(2)} EUR</td>
                  <td><span className={`badge badge-${inv.status === 'paid' ? 'green' : inv.status === 'overdue' ? 'red' : 'amber'}`}>{inv.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'communications' && (
        <div className="card">
          <table>
            <thead><tr><th>Date</th><th>Canal</th><th>Sujet</th><th>Statut</th></tr></thead>
            <tbody>
              {comms.map((c) => (
                <tr key={c.id}>
                  <td>{new Date(c.created_at).toLocaleDateString('fr-FR')}</td>
                  <td><span className="badge badge-blue">{c.channel}</span></td>
                  <td>{c.subject || '-'}</td>
                  <td><span className={`badge badge-${c.status === 'sent' ? 'green' : 'amber'}`}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
