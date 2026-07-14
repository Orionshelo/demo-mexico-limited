"""
Webhook para recibir leads desde la Landing Page.

Endpoint: POST /api/webhooks/lead
Recibe los datos del formulario y los inserta en Google Sheets.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from services.sheets.sheets_client import SheetsClient
from services.sheets.schema import LeadStatus
from services.whatsapp.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)

lead_webhook_bp = Blueprint("lead_webhook", __name__)


@lead_webhook_bp.route("/api/webhooks/lead", methods=["POST"])
def receive_lead():
    """
    Recibe un nuevo lead desde el formulario de la Landing Page.

    Expected JSON payload:
    {
        "nombre": "Juan Pérez",
        "correo": "juan@example.com",
        "telefono": "+525512345678",
        "empresa": "Artesanías MX",
        "url": "https://instagram.com/artesaniasmx",
        "descripcion": "Vendemos artesanías mexicanas..."
    }
    """
    data = request.json

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    # Validate required fields
    required_fields = ["nombre", "correo", "telefono"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({
            "error": f"Missing required fields: {', '.join(missing)}"
        }), 400

    # Normalize phone number
    phone = _normalize_phone(data["telefono"])

    try:
        sheets = SheetsClient()

        # Check if lead already exists
        existing = sheets.find_lead_by_phone(phone)
        if existing:
            logger.info(f"Lead already exists for phone {phone}, updating.")
            sheets.update_lead(
                existing["_row"],
                {
                    "Nombre": data["nombre"],
                    "Correo": data["correo"],
                    "Empresa": data.get("empresa", ""),
                    "URL": data.get("url", ""),
                    "Descripcion_Producto": data.get("descripcion", ""),
                },
            )
            return jsonify({
                "status": "updated",
                "message": "Lead already existed, data updated.",
                "phone": phone,
            }), 200

        # Insert new lead
        lead_data = {
            "Fecha_Registro": datetime.now(timezone.utc).isoformat(),
            "Nombre": data["nombre"],
            "Correo": data["correo"],
            "Telefono": phone,
            "Empresa": data.get("empresa", ""),
            "URL": data.get("url", ""),
            "Descripcion_Producto": data.get("descripcion", ""),
            "Es_Mexicano": "",  # Will be determined by the agent
            "Estatus": LeadStatus.NUEVO.value,
        }

        row = sheets.insert_lead(lead_data)

        logger.info(f"New lead inserted: {data['nombre']} ({phone}) at row {row}")

        # Contacto inicial proactivo: enviar la plantilla de bienvenida por
        # WhatsApp para arrancar el triaje. Un fallo aquí no debe tumbar el
        # registro del lead (ya quedó guardado en Sheets).
        welcome_sent = _send_welcome(phone, data["nombre"])

        return jsonify({
            "status": "created",
            "message": "Lead registered successfully.",
            "phone": phone,
            "row": row,
            "welcome_sent": welcome_sent,
        }), 201

    except Exception as e:
        logger.error(f"Error processing lead webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _send_welcome(phone: str, name: str) -> bool:
    """
    Envía la plantilla de bienvenida (recepcion_lead) por WhatsApp.
    Aislado en try/except para que un fallo de mensajería no afecte
    el registro del lead.
    """
    try:
        WhatsAppClient().send_welcome_template(to=phone, name=name)
        logger.info(f"Welcome template sent to {phone}")
        return True
    except Exception as e:
        logger.error(f"Could not send welcome template to {phone}: {e}")
        return False


def _normalize_phone(phone: str) -> str:
    """Normaliza el teléfono al formato +52XXXXXXXXXX."""
    phone = phone.strip()
    digits = "".join(c for c in phone if c.isdigit())

    # If 10 digits (Mexican local), add +52
    if len(digits) == 10:
        return f"+52{digits}"
    # If already has country code
    elif len(digits) == 12 and digits.startswith("52"):
        return f"+{digits}"
    # If starts with +
    elif phone.startswith("+"):
        return phone

    return f"+{digits}"
