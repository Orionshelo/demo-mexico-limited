"""
Plantillas de mensajes de WhatsApp Business API.

Estas plantillas deben estar registradas y aprobadas en el
Meta Business Manager. Aquí se definen los nombres y parámetros
para que el código pueda despacharlas vía API.
"""

from dataclasses import dataclass


@dataclass
class WhatsAppTemplate:
    """Definición de una plantilla de WhatsApp."""
    name: str              # Nombre registrado en Meta Business Manager
    description: str       # Descripción para referencia interna
    param_count: int       # Número de parámetros {{1}}, {{2}}, etc.
    body_preview: str      # Preview del texto (para logs/debugging)


# ── Template Definitions ──────────────────────────────────────────

TEMPLATE_RECEPCION_LEAD = WhatsAppTemplate(
    name="recepcion_lead",
    description="Bienvenida al lead que llega desde la Landing Page",
    param_count=1,
    body_preview=(
        "¡Hola {{1}}! Bienvenid@ a Mexico Limited. Hemos recibido tu solicitud. "
        "Para poder ayudarte a escalar tu negocio y darte acceso a nuestros "
        "beneficios, me gustaría hacerte un par de preguntas rápidas. "
        "¿Tu producto es 100% hecho en México?"
    ),
)

TEMPLATE_ENVIO_PAGO = WhatsAppTemplate(
    name="envio_datos_pago",
    description="Envío de datos bancarios para pago de inscripción",
    param_count=2,
    body_preview=(
        "¡Excelente perfil, {{1}}! Tienes todo para crecer con nosotros. "
        "Para iniciar tu onboarding y habilitar tu ecosistema digital, "
        "por favor realiza tu pago o transferencia a la siguiente cuenta: {{2}}. "
        "Una vez hecho, mándame una foto del comprobante por aquí mismo."
    ),
)

TEMPLATE_ONBOARDING_APROBADO = WhatsAppTemplate(
    name="onboarding_aprobado",
    description="Confirmación de pago y envío de recursos de onboarding",
    param_count=3,
    body_preview=(
        "¡Pago confirmado, {{1}}! Oficialmente eres parte de Mexico Limited. "
        "Aquí tienes tu guía paso a paso: {{2}}. "
        "Por favor, agenda tu llamada de arranque en este enlace: {{3}}."
    ),
)


# ── Template Registry ────────────────────────────────────────────

ALL_TEMPLATES: dict[str, WhatsAppTemplate] = {
    "recepcion_lead": TEMPLATE_RECEPCION_LEAD,
    "envio_datos_pago": TEMPLATE_ENVIO_PAGO,
    "onboarding_aprobado": TEMPLATE_ONBOARDING_APROBADO,
}


def get_template(name: str) -> WhatsAppTemplate:
    """Obtiene una plantilla por nombre. Lanza KeyError si no existe."""
    if name not in ALL_TEMPLATES:
        raise KeyError(
            f"Template '{name}' not found. Available: {list(ALL_TEMPLATES.keys())}"
        )
    return ALL_TEMPLATES[name]


def build_payment_info_string(
    bank_name: str,
    account_name: str,
    clabe: str,
    reference: str = "",
    amount: str = "",
) -> str:
    """
    Construye el string formateado de información de pago
    para usar como parámetro {{2}} en la plantilla de pago.
    """
    parts = [
        f"🏦 Banco: {bank_name}",
        f"📋 Nombre: {account_name}",
        f"🔢 CLABE: {clabe}",
    ]

    if reference:
        parts.append(f"📝 Referencia: {reference}")
    if amount:
        parts.append(f"💰 Monto: {amount}")

    return " | ".join(parts)
