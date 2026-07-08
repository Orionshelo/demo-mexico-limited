'use client';
import { useEffect, useState, CSSProperties } from 'react';
import Link from 'next/link';

export default function Dashboard() {
  const [score, setScore] = useState<number>(0);
  const [company, setCompany] = useState('');
  const [matches, setMatches] = useState<any[]>([]);

  useEffect(() => {
    const savedScore = localStorage.getItem('ml_diagnostic_score') || '0';
    const onboarding = JSON.parse(localStorage.getItem('ml_onboarding') || '{}');
    const savedMatches = JSON.parse(localStorage.getItem('ml_matches') || '[]');
    
    setScore(parseInt(savedScore));
    setCompany(onboarding.companyName || 'Tu Empresa');
    setMatches(savedMatches);
  }, []);

  return (
    <main className="page-wrapper container" style={{ padding: '2rem 0' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
        <h2>Hola, {company}</h2>
        <Link href="/login" className="btn btn-secondary">Cerrar Sesión</Link>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        
        {/* Left Column - Score */}
        <div className="glass-panel animate-fade-in" style={{ textAlign: 'center' }}>
          <h3>Nivel de Madurez Digital</h3>
          <p style={{ fontSize: '0.875rem' }}>Basado en tu diagnóstico</p>
          
          <div 
            className="score-circle" 
            style={{ '--score': score } as CSSProperties}
          >
            <span className="score-value">{score}%</span>
          </div>
          
          <p style={{ fontWeight: 600, color: score > 70 ? '#10b981' : score > 40 ? '#f59e0b' : '#ef4444' }}>
            {score > 70 ? 'Avanzado' : score > 40 ? 'Intermedio' : 'Inicial'}
          </p>
          <p style={{ fontSize: '0.875rem' }}>
            Aún hay áreas de oportunidad para escalar tus ventas y mejorar tu rentabilidad.
          </p>
        </div>

        {/* Right Column - Recommendations */}
        <div className="glass-panel animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <h3>Oferta de Valor Recomendada</h3>
          <p>La Inteligencia Artificial ha seleccionado los siguientes apoyos de Mexico Limited para ti:</p>
          
          <div className="grid" style={{ marginTop: '2rem' }}>
            {matches.length > 0 ? matches.map((match, i) => (
              <div key={i} style={{ 
                padding: '1.5rem', 
                backgroundColor: 'var(--input-bg)', 
                borderRadius: '8px', 
                borderLeft: '4px solid var(--primary)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <h4 style={{ margin: 0 }}>{match.name}</h4>
                  <p style={{ margin: '0.5rem 0 0', fontSize: '0.875rem' }}>{match.description}</p>
                </div>
                <div style={{ marginLeft: '1rem', textAlign: 'right' }}>
                  <span style={{ 
                    display: 'inline-block', 
                    padding: '0.25rem 0.5rem', 
                    backgroundColor: 'var(--card-bg)',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    color: 'var(--accent)',
                    fontWeight: 600
                  }}>Match {match.match_score}%</span>
                  <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', marginTop: '1rem' }}>
                    Solicitar
                  </button>
                </div>
              </div>
            )) : (
              <div style={{ padding: '2rem', textAlign: 'center', backgroundColor: 'var(--input-bg)', borderRadius: '8px' }}>
                <p>No se pudieron cargar las recomendaciones en este momento.</p>
                <p style={{ fontSize: '0.875rem' }}>(Asegúrate de que el backend en Flask esté corriendo en el puerto 5000)</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </main>
  );
}
