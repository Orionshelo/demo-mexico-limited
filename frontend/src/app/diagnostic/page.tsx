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
      id: 'q1',
      text: '¿Cuentas con una página web o tienda en línea activa?',
      options: [
        { label: 'No, nada', value: 0 },
        { label: 'Solo redes sociales', value: 33 },
        { label: 'Sí, pero vende poco', value: 66 },
        { label: 'Sí, es mi canal principal', value: 100 }
      ]
    },
    {
      id: 'q2',
      text: '¿Cómo manejas tus redes sociales (Instagram/Facebook)?',
      options: [
        { label: 'No tengo', value: 0 },
        { label: 'Publico de vez en cuando', value: 33 },
        { label: 'Tengo un calendario y publico seguido', value: 66 },
        { label: 'Hago pauta (Ads) y tengo estrategia', value: 100 }
      ]
    },
    {
      id: 'q3',
      text: '¿Qué tan formal está tu contabilidad y aspecto legal?',
      options: [
        { label: 'No estoy constituido ni declaro', value: 0 },
        { label: 'Declaro como persona física', value: 33 },
        { label: 'Estoy en proceso de formalizar mi empresa', value: 66 },
        { label: 'Constituido, con contador y marca registrada', value: 100 }
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
    
    // Calculate Score
    const totalScore = Object.values(finalAnswers).reduce((a, b) => a + b, 0) / questions.length;
    
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
      localStorage.setItem('ml_diagnostic_score', Math.round(totalScore).toString());
      localStorage.setItem('ml_matches', JSON.stringify(data.matches || []));
      
      router.push('/dashboard');
    } catch (error) {
      console.error("Error connecting to backend", error);
      // Fallback
      localStorage.setItem('ml_diagnostic_score', Math.round(totalScore).toString());
      localStorage.setItem('ml_matches', JSON.stringify([]));
      router.push('/dashboard');
    }
  };

  return (
    <main className="page-wrapper container">
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%', textAlign: 'center' }}>
        <div style={{ marginBottom: '2rem' }}>
          <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Paso {currentStep + 1} de {questions.length}</span>
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
