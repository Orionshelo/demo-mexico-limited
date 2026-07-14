# Mexico Limited — AI Agent Backend

Backend del Agente de IA de Mexico Limited. Automatiza la captación, triaje, conversión y onboarding de leads vía WhatsApp, integrado con Google Sheets como base de datos.

## Stack Tecnológico

- **Python 3.9+** / **Flask** — API y Webhooks
- **OpenAI (GPT-4o-mini)** — Motor de conversación del agente
- **Google Sheets API (gspread)** — Base de datos de leads
- **Meta WhatsApp Cloud API** — Mensajería con emprendedores
- **SendGrid** — Notificaciones al ejecutivo (comprobantes, handoff)
- **APScheduler** — Cron job para detección de pagos aprobados

## Estructura

```
backend/
├── app.py                    # Entry point (Application Factory)
├── config.py                 # Variables de entorno centralizadas
├── agent/                    # Motor del Agente de IA
│   ├── orchestrator.py       # Máquina de estados principal
│   └── prompts/              # System prompt y plantillas WA
├── api/webhooks/             # Endpoints de webhook
│   ├── lead_webhook.py       # POST /api/webhooks/lead
│   └── whatsapp_webhook.py   # GET+POST /api/webhooks/whatsapp
├── services/
│   ├── sheets/               # CRUD Google Sheets
│   ├── whatsapp/             # Meta API client + parser
│   └── notifications/        # Email al ejecutivo
├── utils/
│   ├── scoring.py            # Algoritmo de madurez digital (0-100)
│   └── nurture.py            # Lógica de seguimiento (nurturing) — pura
├── jobs/
│   ├── payment_watcher.py    # Cron de detección de pagos
│   └── nurture_watcher.py    # Cron de seguimiento de leads fríos
└── tests/                    # Unit tests
```

## Flujo del Agente (end-to-end)

1. **Registro** — La Landing Page hace `POST /api/webhooks/lead`. El lead se
   guarda en Google Sheets (CRM) y el agente **envía automáticamente la
   plantilla de bienvenida** por WhatsApp para iniciar el triaje.
2. **Triaje** — Conversación por WhatsApp: reglas de descarte (mexicano /
   multinivel / perecedero) y extracción de entidades.
3. **Score de madurez** — Se calcula (0-100) y se guarda con su desglose.
4. **Pago** — Si califica, se envían los datos de pago; el lead manda su
   comprobante (imagen) y el ejecutivo lo valida por email.
5. **Onboarding** — Al aprobarse el pago, el `payment_watcher` envía la guía
   y el enlace de Calendly.
6. **Nurturing** — El `nurture_watcher` re-engancha por WhatsApp/email a los
   leads que se enfrían:
   - `sin_respuesta`: registrados que nunca contestaron (Estatus "Nuevo").
   - `pago_pendiente`: calificados que no completan el pago.

   La cadencia y el tope de mensajes viven en `utils/nurture.py`. El avance se
   persiste en las columnas `Nurture_Etapa` y `Ultimo_Nurture`.

   > **⚠️ Producción:** los mensajes de WhatsApp fuera de la ventana de 24h
   > requieren **plantillas pre-aprobadas por Meta**. En la demo se envían como
   > texto libre; para producción, registra cada mensaje de la secuencia como
   > plantilla y despáchalo con `send_template`.

## Desarrollo Local

```bash
# 1. Crear y activar venv
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales reales

# 4. Correr el servidor
python app.py
# → http://localhost:5000
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/match` | Matching de servicios por similitud (demo original) |
| `POST` | `/api/webhooks/lead` | Recibe leads del formulario de la Landing Page |
| `GET` | `/api/webhooks/whatsapp` | Verificación del webhook de Meta |
| `POST` | `/api/webhooks/whatsapp` | Mensajes entrantes de WhatsApp |
| `GET` | `/api/health` | Health check y validación de config |

### `POST /api/webhooks/lead`

```json
{
  "nombre": "Juan Pérez",
  "correo": "juan@example.com",
  "telefono": "+525512345678",
  "empresa": "Artesanías MX",
  "url": "https://instagram.com/artesaniasmx",
  "descripcion": "Vendemos artesanías mexicanas..."
}
```

---

## Deploy en Render

### 1. Crear Web Service en Render
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Environment:** Python 3

### 2. Variables de Entorno en Render
Configurar en el dashboard de Render (Environment → Add Environment Variable):

| Variable | Valor |
|---|---|
| `META_WHATSAPP_TOKEN` | Token de Meta Business API |
| `META_PHONE_NUMBER_ID` | ID del número de WhatsApp |
| `META_VERIFY_TOKEN` | Token secreto para verificar webhook |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | **Pegar el JSON completo** del Service Account |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID de la hoja de Google Sheets |
| `OPENAI_API_KEY` | API key de OpenAI |
| `SENDGRID_API_KEY` | API key de SendGrid |
| `EXECUTIVE_EMAIL` | Email del ejecutivo de validación |

> **⚠️ Nota:** En Render, usa `GOOGLE_SHEETS_CREDENTIALS_JSON` (el JSON completo)
> en lugar de `GOOGLE_SHEETS_CREDENTIALS_FILE` (que es para desarrollo local).

### 3. Configurar Webhook de Meta
Una vez desplegado, el URL del webhook será:
```
https://tu-servicio.onrender.com/api/webhooks/whatsapp
```
Configurar en Meta Business Manager → WhatsApp → Configuration → Webhook URL.

### 4. Consideración: Render Free Tier
El tier gratuito de Render suspende el servicio tras 15 minutos de inactividad.
Para una demo, esto funciona, pero el primer mensaje de WhatsApp podría tardar ~30 segundos
mientras el servicio se reactiva. Para producción, usar el tier Starter ($7/mes).
