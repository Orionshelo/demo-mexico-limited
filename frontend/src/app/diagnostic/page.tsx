'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Diagnostic() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const questions = [
    {
      id: 'presencia_digital',
      text: '¿Cuentas con una página web o tienda en línea activa?',
      dimension: 'Presencia Digital',
      maxPoints: 30,
      options: [
        { label: 'No, no tengo presencia digital', value: 0 },
        { label: 'Solo tengo redes sociales (Instagram, Facebook, etc.)', value: 15 },
        { label: 'Sí, tengo un sitio web con capacidad de venta', value: 30 },
      ]
    },
    {
      id: 'traccion_ventas',
      text: '¿Cómo vendes actualmente?',
      dimension: 'Tracción y Ventas',
      maxPoints: 30,
      options: [
        { label: 'Aún solo tengo la idea, no he vendido', value: 0 },
        { label: 'Solo vendo presencialmente / en tienda física', value: 10 },
        { label: 'Vendo por DMs, WhatsApp o redes sociales', value: 15 },
        { label: 'Vendo online de forma recurrente', value: 30 },
      ]
    },
    {
      id: 'formalizacion',
      text: '¿Tu negocio está formalizado legalmente?',
      dimension: 'Formalización',
      maxPoints: 20,
      options: [
        { label: 'No, soy informal / no tengo RFC', value: 0 },
        { label: 'Sí, soy persona física o moral con RFC', value: 20 },
      ]
    },
    {
      id: 'uso_herramientas',
      text: '¿Usas herramientas digitales para gestionar tu negocio?',
      dimension: 'Uso de Herramientas',
      maxPoints: 20,
      options: [
        { label: 'No, todo lo hago manualmente (Excel, libreta, etc.)', value: 0 },
        { label: 'Sí, uso software o apps (CRM, inventario, facturación...)', value: 20 },
      ]
    }
  ];

  const handleSelect = (value: number) => {
    const newAnswers = { ...answers, [questions[currentStep].id]: value };
    setAnswers(newAnswers);
    
    if (currentStep < questions.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      finishDiagnostic(newAnswers);
    }
  };

  const finishDiagnostic = async (finalAnswers: Record<string, number>) => {
    setIsSubmitting(true);
    
    // Calculate Score — sum of all dimension points (max 100)
    const totalScore = Object.values(finalAnswers).reduce((a, b) => a + b, 0);
    
    // Categorize
    let nivel = 'Inicial';
    if (totalScore > 70) nivel = 'Avanzado';
    else if (totalScore > 30) nivel = 'Intermedio';

    // Get Needs from Onboarding
    const onboardingData = JSON.parse(localStorage.getItem('ml_onboarding') || '{}');
    const needs = onboardingData.productDescription || "Ventas, marketing y e-commerce";

    try {
      // Call Flask Backend using environment variable
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      const res = await fetch(`${apiUrl}/api/match`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ needs })
      });
      
      const data = await res.json();
      
      // Save everything to localStorage for the Dashboard to read
      localStorage.setItem('ml_diagnostic_score', totalScore.toString());
      localStorage.setItem('ml_diagnostic_nivel', nivel);
      localStorage.setItem('ml_diagnostic_desglose', JSON.stringify(finalAnswers));
      localStorage.setItem('ml_matches', JSON.stringify(data.matches || []));
      
      router.push('/dashboard');
    } catch (error) {
      console.error("Error connecting to backend", error);
      // Fallback
      localStorage.setItem('ml_diagnostic_score', totalScore.toString());
      localStorage.setItem('ml_diagnostic_nivel', nivel);
      localStorage.setItem('ml_diagnostic_desglose', JSON.stringify(finalAnswers));
      localStorage.setItem('ml_matches', JSON.stringify([]));
      router.push('/dashboard');
    }
  };

  return (
    <main className="page-wrapper container">
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%', textAlign: 'center' }}>
        <div style={{ marginBottom: '2rem' }}>
          <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Paso {currentStep + 1} de {questions.length}</span>
          <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '4px 0 0' }}>
            {questions[currentStep].dimension} (Máx. {questions[currentStep].maxPoints} pts)
          </p>
          <div style={{ width: '100%', backgroundColor: 'var(--secondary)', height: '6px', borderRadius: '3px', marginTop: '10px' }}>
            <div style={{ 
              width: `${((currentStep + 1) / questions.length) * 100}%`, 
              backgroundColor: 'var(--primary)', 
              height: '100%', 
              borderRadius: '3px',
              transition: 'width 0.3s ease'
            }}></div>
          </div>
        </div>

        {isSubmitting ? (
          <div>
            <h2>Analizando tu perfil...</h2>
            <p>Nuestra Inteligencia Artificial está buscando los mejores apoyos para ti.</p>
            <div style={{ marginTop: '2rem' }} className="animate-fade-in">⏳</div>
          </div>
        ) : (
          <div>
            <h2 style={{ marginBottom: '2rem' }}>{questions[currentStep].text}</h2>
            
            <div className="grid">
              {questions[currentStep].options.map((opt, i) => (
                <button 
                  key={i} 
                  className="btn btn-secondary" 
                  style={{ textAlign: 'left', justifyContent: 'flex-start', padding: '1rem' }}
                  onClick={() => handleSelect(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
