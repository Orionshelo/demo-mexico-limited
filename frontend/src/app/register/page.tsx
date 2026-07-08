'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function Register() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    // En un escenario real, aquí se llamaría a Supabase:
    // const { error } = await supabase.auth.signUp({ email, password });
    // Para la demo, lo simularemos redirigiendo al onboarding.
    router.push('/onboarding');
  };

  return (
    <main className="page-wrapper container">
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '450px', margin: '0 auto', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ color: 'var(--primary)' }}>Regístrate</h2>
          <p>Crea tu cuenta en Mexico Limited</p>
        </div>
        
        <form onSubmit={handleRegister}>
          <div className="form-group">
            <label className="form-label">Correo Electrónico</label>
            <input 
              type="email" 
              required
              className="form-input" 
              placeholder="tu@correo.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">Contraseña</label>
            <input 
              type="password" 
              required
              className="form-input" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-secondary" style={{ width: '100%', marginTop: '1rem' }}>
            Crear Cuenta
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem' }}>
          ¿Ya tienes cuenta?{' '}
          <Link href="/login" style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'none' }}>
            Inicia Sesión
          </Link>
        </div>
      </div>
    </main>
  );
}
