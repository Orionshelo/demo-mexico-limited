"""
Parser de payloads del webhook de Meta WhatsApp Business API.

Normaliza los diferentes tipos de mensajes entrantes (text, image,
button_reply, interactive) en una estructura uniforme para el orquestador.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessage:
    """Mensaje normalizado de WhatsApp."""
    phone: str                          # Número del remitente (+52...)
    display_name: str                   # Nombre del perfil de WhatsApp
    message_type: str                   # "text", "image", "button_reply", "interactive", "unknown"
    text: str = ""                      # Contenido de texto
    media_id: Optional[str] = None      # ID del media (imagen, documento)
    media_mime_type: Optional[str] = None
    button_payload: Optional[str] = None  # Payload del botón seleccionado
    timestamp: str = ""                 # Timestamp del mensaje
    message_id: str = ""                # ID único del mensaje en Meta
    raw_payload: dict = field(default_factory=dict)  # Payload original para debugging


def parse_webhook_payload(payload: dict) -> list[WhatsAppMessage]:
    """
    Parsea el payload del webhook de Meta y extrae los mensajes.

    El payload de Meta puede contener múltiples entries y changes.
    Cada change puede tener múltiples mensajes.

    Args:
        payload: JSON body del webhook POST de Meta.

    Returns:
        Lista de WhatsAppMessage normalizados.

    Reference:
        https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
    """
    messages: list[WhatsAppMessage] = []

    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Only process "messages" field (not statuses)
            if "messages" not in value:
                continue

            contacts = value.get("contacts", [])
            contact_map: dict[str, str] = {}
            for contact in contacts:
                wa_id = contact.get("wa_id", "")
                name = contact.get("profile", {}).get("name", "")
                contact_map[wa_id] = name

            for msg in value.get("messages", []):
                parsed = _parse_single_message(msg, contact_map)
                if parsed:
                    messages.append(parsed)

    if not messages:
        logger.debug(f"No messages found in webhook payload: {payload}")

    return messages


def _parse_single_message(
    msg: dict, contact_map: dict[str, str]
) -> Optional[WhatsAppMessage]:
    """Parse a single message object from the webhook payload."""
    phone = msg.get("from", "")
    msg_type = msg.get("type", "unknown")
    timestamp = msg.get("timestamp", "")
    message_id = msg.get("id", "")
    display_name = contact_map.get(phone, "")

    base = WhatsAppMessage(
        phone=_normalize_phone(phone),
        display_name=display_name,
        message_type=msg_type,
        timestamp=timestamp,
        message_id=message_id,
        raw_payload=msg,
    )

    if msg_type == "text":
        base.text = msg.get("text", {}).get("body", "")

    elif msg_type == "image":
        image_data = msg.get("image", {})
        base.media_id = image_data.get("id")
        base.media_mime_type = image_data.get("mime_type", "image/jpeg")
        base.text = image_data.get("caption", "")

    elif msg_type == "document":
        doc_data = msg.get("document", {})
        base.media_id = doc_data.get("id")
        base.media_mime_type = doc_data.get("mime_type")
        base.text = doc_data.get("caption", "")

    elif msg_type == "button":
        # Reply from a template button
        button_data = msg.get("button", {})
        base.text = button_data.get("text", "")
        base.button_payload = button_data.get("payload", "")
        base.message_type = "button_reply"

    elif msg_type == "interactive":
        interactive = msg.get("interactive", {})
        interactive_type = interactive.get("type", "")
        if interactive_type == "button_reply":
            reply = interactive.get("button_reply", {})
            base.text = reply.get("title", "")
            base.button_payload = reply.get("id", "")
        elif interactive_type == "list_reply":
            reply = interactive.get("list_reply", {})
            base.text = reply.get("title", "")
            base.button_payload = reply.get("id", "")
        base.message_type = "interactive"

    elif msg_type == "reaction":
        # Ignorar reacciones
        return None

    else:
        base.message_type = "unknown"
        logger.warning(f"Unknown message type: {msg_type}")

    return base


def _normalize_phone(phone: str) -> str:
    """
    Normaliza el número de teléfono al formato +52XXXXXXXXXX.
    Meta envía los números sin el +, solo los dígitos.
    """
    phone = phone.strip()

    # Remove any non-digit characters
    digits_only = "".join(c for c in phone if c.isdigit())

    # Ensure it starts with country code
    if not phone.startswith("+"):
        phone = f"+{digits_only}"

    return phone
