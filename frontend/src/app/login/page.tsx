'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    // En un escenario real, aquí se llamaría a Supabase:
    // const { error } = await supabase.auth.signInWithPassword({ email, password });
    
    // Si ya existe un registro previo de onboarding en el navegador, 
    // lo enviamos directo al dashboard, sino al onboarding.
    const onboarding = localStorage.getItem('ml_onboarding');
    if (onboarding) {
      router.push('/dashboard');
    } else {
      router.push('/onboarding');
    }
  };

  return (
    <main className="page-wrapper container">
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '450px', margin: '0 auto', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ color: 'var(--primary)' }}>Iniciar Sesión</h2>
          <p>Bienvenido de vuelta a Mexico Limited</p>
        </div>
        
        <form onSubmit={handleLogin}>
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

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
            Ingresar
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem' }}>
          ¿No tienes cuenta?{' '}
          <Link href="/register" style={{ color: 'var(--accent)', fontWeight: 600, textDecoration: 'none' }}>
            Regístrate aquí
          </Link>
        </div>
      </div>
    </main>
  );
}
