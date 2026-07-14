"""
Simulador de WhatsApp para demos sin verificación de Meta.

Endpoints:
  POST /api/simulator/chat  — Envía un mensaje simulado y recibe la respuesta del agente.
  GET  /api/simulator        — Sirve la interfaz de chat.
"""

import asyncio
import logging
import time

from flask import Blueprint, request, jsonify, send_from_directory

from services.whatsapp.payload_parser import WhatsAppMessage
from agent.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

simulator_bp = Blueprint("simulator", __name__)


class MockWhatsAppClient:
    """
    Cliente falso de WhatsApp que captura los mensajes
    en lugar de enviarlos a la API de Meta.
    """

    def __init__(self):
        self.sent_messages: list[dict] = []

    def send_text_message(self, to: str, text: str) -> dict:
        self.sent_messages.append({"to": to, "text": text, "type": "text"})
        return {"status": "simulated"}

    def send_template(
        self, to: str, template_name: str, parameters: list[str],
        language_code: str = "es_MX"
    ) -> dict:
        self.sent_messages.append({
            "to": to,
            "type": "template",
            "template": template_name,
            "parameters": parameters,
        })
        return {"status": "simulated"}

    def send_welcome_template(self, to: str, name: str) -> dict:
        return self.send_template(to, "recepcion_lead", [name])

    def send_payment_template(
        self, to: str, name: str, payment_info: str
    ) -> dict:
        return self.send_template(
            to, "envio_datos_pago", [name, payment_info]
        )

    def send_onboarding_template(
        self, to: str, name: str, guide_link: str, calendly_link: str
    ) -> dict:
        return self.send_template(
            to, "onboarding_aprobado", [name, guide_link, calendly_link]
        )

    def mark_as_read(self, message_id: str) -> dict:
        return {"status": "simulated"}

    def download_media(self, media_id: str):
        return None

    def get_media_url(self, media_id: str):
        return None


@simulator_bp.route("/api/simulator/chat", methods=["POST"])
def simulator_chat():
    """
    Recibe un mensaje de texto simulado y lo procesa a través del
    orquestador del agente. Devuelve la(s) respuesta(s) del bot.

    Request body:
        {
            "phone": "+525500000001",
            "name": "Demo User",
            "message": "Hola, quiero información"
        }

    Response:
        {
            "responses": [
                {"to": "...", "text": "...", "type": "text"},
                ...
            ]
        }
    """
    data = request.json
    if not data or "message" not in data:
        return jsonify({"error": "Se requiere un campo 'message'"}), 400

    phone = data.get("phone", "+525500000001")
    name = data.get("name", "Demo User")
    text = data.get("message", "")

    # Create a fake WhatsAppMessage
    message = WhatsAppMessage(
        phone=phone,
        display_name=name,
        message_type="text",
        text=text,
        timestamp=str(int(time.time())),
        message_id=f"sim_{int(time.time())}",
    )

    # Create orchestrator with mock WhatsApp client
    mock_wa = MockWhatsAppClient()
    orchestrator = AgentOrchestrator()
    orchestrator.whatsapp = mock_wa

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(orchestrator.process_message(message))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Simulator error: {e}", exc_info=True)
        return jsonify({
            "responses": [{
                "to": phone,
                "text": f"Error procesando el mensaje: {str(e)}",
                "type": "error",
            }]
        }), 500

    return jsonify({"responses": mock_wa.sent_messages})


@simulator_bp.route("/api/simulator", methods=["GET"])
def simulator_ui():
    """Sirve la interfaz de chat del simulador."""
    return send_from_directory("static", "simulator.html")
