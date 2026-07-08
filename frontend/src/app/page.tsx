import Link from 'next/link';
import './globals.css';

export default function Home() {
  return (
    <main className="page-wrapper container">
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center', padding: '4rem 2rem' }}>
        <h1 style={{ marginBottom: '1rem', color: 'var(--foreground)' }}>
          <span style={{ color: 'var(--primary)' }}>Mexico</span> Limited
        </h1>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>Potencia tu Emprendimiento</h2>
        <p style={{ fontSize: '1.125rem', maxWidth: '600px', margin: '0 auto 3rem' }}>
          Únete a la plataforma integral que conecta tus necesidades con el ecosistema de apoyo más grande de México. Diagnóstico de madurez, CRM y vinculación inteligente.
        </p>
        
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <Link href="/register" className="btn btn-secondary">
            Regístrate
          </Link>
          <Link href="/login" className="btn btn-primary" style={{ backgroundColor: '#ffffff', color: 'var(--primary)', border: '2px solid var(--primary)' }}>
            Iniciar Sesión
          </Link>
        </div>
      </div>
      
      {/* Decorative background blur elements */}
      <div style={{
        position: 'fixed',
        top: '20%',
        left: '10%',
        width: '300px',
        height: '300px',
        background: 'var(--primary)',
        filter: 'blur(120px)',
        opacity: 0.1,
        zIndex: -1,
        borderRadius: '50%'
      }}></div>
      <div style={{
        position: 'fixed',
        bottom: '10%',
        right: '10%',
        width: '400px',
        height: '400px',
        background: 'var(--accent)',
        filter: 'blur(150px)',
        opacity: 0.1,
        zIndex: -1,
        borderRadius: '50%'
      }}></div>
    </main>
  );
}
