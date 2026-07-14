"""
Configuración centralizada del backend.
Lee variables de entorno desde .env con valores por defecto seguros.
"""

import os
from dotenv import load_dotenv

# override=True hace que el archivo .env tenga prioridad sobre variables de
# entorno preexistentes del sistema (útil en desarrollo local, donde un
# placeholder viejo en el entorno no debe pisar el .env). En producción
# (Render) no existe .env, así que esto es un no-op y las env vars mandan.
load_dotenv(override=True)


# ── Meta WhatsApp Business API ────────────────────────────────────

META_WHATSAPP_TOKEN: str = os.getenv("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")
META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "mexico-limited-verify-2024")
META_API_VERSION: str = os.getenv("META_API_VERSION", "v21.0")
META_API_BASE_URL: str = f"https://graph.facebook.com/{META_API_VERSION}"


# ── Google Sheets ─────────────────────────────────────────────────

GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
)
# Alternative: paste the entire JSON content as an env var (for Render/Cloud)
GOOGLE_SHEETS_CREDENTIALS_JSON: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
GOOGLE_SHEETS_SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
GOOGLE_SHEETS_WORKSHEET_NAME: str = os.getenv(
    "GOOGLE_SHEETS_WORKSHEET_NAME", "Nuevos_Leads"
)


# ── LLM (OpenAI) ─────────────────────────────────────────────────

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# ── Admin ────────────────────────────────────────────────────────

ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "demo123")


# ── Notificaciones ────────────────────────────────────────────────

SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
NOTIFICATION_FROM_EMAIL: str = os.getenv(
    "NOTIFICATION_FROM_EMAIL", "agente@mexicolimited.com"
)
EXECUTIVE_EMAIL: str = os.getenv("EXECUTIVE_EMAIL", "")
EXECUTIVE_PHONE: str = os.getenv("EXECUTIVE_PHONE", "")


# ── Datos de Pago (estáticos, configurables) ──────────────────────

PAYMENT_BANK_NAME: str = os.getenv("PAYMENT_BANK_NAME", "BBVA")
PAYMENT_ACCOUNT_NAME: str = os.getenv(
    "PAYMENT_ACCOUNT_NAME", "Mexico Limited S.A. de C.V."
)
PAYMENT_CLABE: str = os.getenv("PAYMENT_CLABE", "")
PAYMENT_REFERENCE: str = os.getenv("PAYMENT_REFERENCE", "")
PAYMENT_AMOUNT: str = os.getenv("PAYMENT_AMOUNT", "")


# ── Onboarding Links ─────────────────────────────────────────────

CALENDLY_LINK: str = os.getenv("CALENDLY_LINK", "https://calendly.com/mexicolimited")
ONBOARDING_GUIDE_LINK: str = os.getenv("ONBOARDING_GUIDE_LINK", "")
CLASSROOM_LINK: str = os.getenv("CLASSROOM_LINK", "")
TIENDANUBE_LINK: str = os.getenv("TIENDANUBE_LINK", "")


# ── Application ───────────────────────────────────────────────────

FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
PAYMENT_POLL_INTERVAL_MINUTES: int = int(
    os.getenv("PAYMENT_POLL_INTERVAL_MINUTES", "5")
)
# Intervalo del cron de nurturing (seguimiento de leads fríos).
# La cadencia real es de horas/días; basta con revisar cada hora.
NURTURE_POLL_INTERVAL_MINUTES: int = int(
    os.getenv("NURTURE_POLL_INTERVAL_MINUTES", "60")
)

# Human handoff keywords — agent watches for these in user messages
HUMAN_HANDOFF_KEYWORDS: list[str] = [
    "hablar con alguien",
    "hablar con una persona",
    "quiero hablar con un humano",
    "representante",
    "ejecutivo",
    "agente real",
    "no entiendo",
    "estoy frustrado",
    "esto no funciona",
    "basta",
    "ya no quiero",
]


def validate_required_config() -> list[str]:
    """
    Valida que las variables de entorno críticas estén configuradas.
    Retorna una lista de variables faltantes.
    """
    required = {
        "META_WHATSAPP_TOKEN": META_WHATSAPP_TOKEN,
        "META_PHONE_NUMBER_ID": META_PHONE_NUMBER_ID,
        "GOOGLE_SHEETS_SPREADSHEET_ID": GOOGLE_SHEETS_SPREADSHEET_ID,
        "OPENAI_API_KEY": OPENAI_API_KEY,
    }

    missing = [name for name, value in required.items() if not value]
    return missing
