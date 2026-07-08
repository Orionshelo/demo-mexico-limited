'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Onboarding() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    companyName: '',
    productDescription: '',
    isMexican: 'yes',
    hasSales: 'yes'
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({...formData, [e.target.name]: e.target.value});
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Simulate saving to Supabase, then redirect to diagnostic
    localStorage.setItem('ml_onboarding', JSON.stringify(formData));
    router.push('/diagnostic');
  };

  return (
    <main className="page-wrapper container">
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
        <h2>Onboarding: Perfil de tu Empresa</h2>
        <p>Cuéntanos sobre tu negocio para ofrecerte los mejores apoyos.</p>
        
        <form onSubmit={handleSubmit} style={{ marginTop: '2rem' }}>
          <div className="form-group">
            <label className="form-label">Nombre de tu Marca o Empresa</label>
            <input 
              type="text" 
              name="companyName" 
              required
              className="form-input" 
              placeholder="Ej. Salsas Don José" 
              value={formData.companyName}
              onChange={handleChange}
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">¿Tu producto es 100% Mexicano?</label>
            <select name="isMexican" className="form-input" value={formData.isMexican} onChange={handleChange}>
              <option value="yes">Sí, es 100% mexicano</option>
              <option value="no">No, importo productos o materiales</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">¿Ya tienes ventas actuales?</label>
            <select name="hasSales" className="form-input" value={formData.hasSales} onChange={handleChange}>
              <option value="yes">Sí, ya tengo ventas probadas</option>
              <option value="no">No, aún estoy en etapa de idea o desarrollo</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Describe tu producto y tus necesidades principales</label>
            <textarea 
              name="productDescription"
              required
              className="form-input" 
              rows={4} 
              placeholder="Vendemos salsas artesanales, necesitamos ayuda para vender en línea y llevar la contabilidad..."
              value={formData.productDescription}
              onChange={handleChange}
            ></textarea>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
            Continuar al Diagnóstico Digital
          </button>
        </form>
      </div>
      
      {/* Decorative background */}
      <div style={{
        position: 'fixed',
        top: '10%',
        right: '20%',
        width: '300px',
        height: '300px',
        background: 'var(--accent)',
        filter: 'blur(100px)',
        opacity: 0.15,
        zIndex: -1,
        borderRadius: '50%'
      }}></div>
    </main>
  );
}
