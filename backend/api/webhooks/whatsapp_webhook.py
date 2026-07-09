"""
Webhook para mensajes entrantes de WhatsApp (Meta Cloud API).

Endpoints:
  GET  /api/webhooks/whatsapp  — Verificación del webhook (Meta challenge).
  POST /api/webhooks/whatsapp  — Recepción de mensajes entrantes.
"""

import asyncio
import logging

from flask import Blueprint, request, jsonify

from config import META_VERIFY_TOKEN
from services.whatsapp.payload_parser import parse_webhook_payload
from agent.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

whatsapp_webhook_bp = Blueprint("whatsapp_webhook", __name__)


@whatsapp_webhook_bp.route("/api/webhooks/whatsapp", methods=["GET"])
def verify_webhook():
    """
    Verificación del webhook de Meta.

    Meta envía un GET con:
      - hub.mode = "subscribe"
      - hub.verify_token = tu token secreto
      - hub.challenge = un string que debes devolver

    Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully.")
        return challenge, 200
    else:
        logger.warning(
            f"WhatsApp webhook verification failed. "
            f"mode={mode}, token_match={token == META_VERIFY_TOKEN}"
        )
        return "Forbidden", 403


@whatsapp_webhook_bp.route("/api/webhooks/whatsapp", methods=["POST"])
def receive_message():
    """
    Recibe mensajes entrantes de WhatsApp.

    Meta envía un POST con el payload del mensaje.
    Parseamos y delegamos al orquestador del agente.

    IMPORTANT: Siempre retornamos 200 rápidamente a Meta para
    evitar reintentos. El procesamiento se hace de forma asíncrona.
    """
    payload = request.json

    if not payload:
        return jsonify({"status": "no_data"}), 200

    # Parse the webhook payload
    messages = parse_webhook_payload(payload)

    if not messages:
        # This could be a status update (delivered, read), not a message
        logger.debug("No messages in webhook payload (possibly a status update).")
        return jsonify({"status": "ok"}), 200

    # Process each message asynchronously
    orchestrator = get_orchestrator()

    for message in messages:
        logger.info(
            f"Incoming message from {message.phone}: "
            f"type={message.message_type}, text={message.text[:100] if message.text else 'N/A'}"
        )
        try:
            # Run the async orchestrator in a new event loop
            # (Flask is synchronous, so we bridge to async here)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(orchestrator.process_message(message))
            finally:
                loop.close()

        except Exception as e:
            logger.error(
                f"Error processing message from {message.phone}: {e}",
                exc_info=True,
            )
            # Don't fail the webhook response — Meta would retry

    return jsonify({"status": "ok"}), 200
