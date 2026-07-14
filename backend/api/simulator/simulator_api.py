"""
Simulador de WhatsApp para demos sin verificación de Meta.

Mantiene la conversación en memoria (no depende de Google Sheets para
el historial), lo cual garantiza continuidad del chat en la demo.

Endpoints:
  POST /api/simulator/chat   — Envía un mensaje simulado y recibe respuesta.
  POST /api/simulator/reset  — Reinicia la conversación.
  GET  /api/simulator        — Sirve la interfaz de chat.
"""

import json
import logging
import re
import time
from collections import defaultdict
from typing import Optional

import openai

from flask import Blueprint, request, jsonify, send_from_directory

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    PAYMENT_BANK_NAME,
    PAYMENT_ACCOUNT_NAME,
    PAYMENT_CLABE,
    PAYMENT_REFERENCE,
    PAYMENT_AMOUNT,
)
from agent.prompts.system_prompt import build_system_prompt
from agent.prompts.templates import build_payment_info_string
from services.sheets.sheets_client import SheetsClient
from services.sheets.schema import LeadStatus
from utils.scoring import calculate_maturity_score

logger = logging.getLogger(__name__)

simulator_bp = Blueprint("simulator", __name__)

# ── In-memory conversation store ──────────────────────────────────
# Key: phone number, Value: list of {"role": ..., "content": ...}
_conversations: dict[str, list[dict]] = defaultdict(list)

# ── In-memory lead data cache ────────────────────────────────────
# Key: phone number, Value: dict with lead fields
_leads: dict[str, dict] = {}

# OpenAI client
_openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)


# ── Endpoints ─────────────────────────────────────────────────────

@simulator_bp.route("/api/simulator/chat", methods=["POST"])
def simulator_chat():
    """
    Procesa un mensaje simulado a través del agente IA.
    Mantiene el historial en memoria para garantizar continuidad.
    """
    data = request.json
    if not data or "message" not in data:
        return jsonify({"error": "Se requiere un campo 'message'"}), 400

    phone = data.get("phone", "+525500000001")
    name = data.get("name", "Demo User")
    text = data.get("message", "").strip()

    if not text:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    # ── Initialize lead if new ────────────────────────────────────
    if phone not in _leads:
        _leads[phone] = {
            "Nombre": name,
            "Telefono": phone,
            "Estatus": LeadStatus.NUEVO.value,
            "Empresa": "",
            "Correo": "",
            "URL": "",
            "Descripcion_Producto": "",
            "Score_Madurez": "",
            "Nivel_Madurez": "",
            "_row": -1,
        }
        # Try to save to Google Sheets (best effort for demo)
        _save_lead_to_sheets(phone)

    lead = _leads[phone]

    # Update name if provided
    if name and name != "Demo User":
        lead["Nombre"] = name

    # Update status if still new
    if lead.get("Estatus") == LeadStatus.NUEVO.value:
        lead["Estatus"] = LeadStatus.EN_TRIAJE.value

    # ── Add user message to history ───────────────────────────────
    _conversations[phone].append({"role": "user", "content": text})

    # ── Build system prompt and call LLM ──────────────────────────
    system_prompt = build_system_prompt(lead)
    llm_response = _call_llm(system_prompt, _conversations[phone])

    if llm_response is None:
        return jsonify({
            "responses": [{
                "to": phone,
                "text": "Disculpa, tuve un problema técnico. ¿Podrías repetir tu mensaje? 🙏",
                "type": "text",
            }]
        })

    # ── Parse response ────────────────────────────────────────────
    user_message, action_data = _parse_llm_response(llm_response)

    # ── Process entities and actions ──────────────────────────────
    entities = action_data.get("entities", {})
    _update_lead_entities(lead, entities)

    action = action_data.get("action", "continue")
    responses = []

    if action == "discard":
        lead["Estatus"] = LeadStatus.DESCARTADO.value
        responses.append({"to": phone, "text": user_message, "type": "text"})

    elif action in ("score_ready", "send_payment"):
        # Calculate score
        score_result = _calculate_score(entities)
        lead["Score_Madurez"] = str(score_result["score"])
        lead["Nivel_Madurez"] = score_result["nivel"]
        lead["Estatus"] = LeadStatus.CALIFICADO.value

        responses.append({"to": phone, "text": user_message, "type": "text"})

        if action == "send_payment":
            payment_info = build_payment_info_string(
                bank_name=PAYMENT_BANK_NAME,
                account_name=PAYMENT_ACCOUNT_NAME,
                clabe=PAYMENT_CLABE,
                reference=PAYMENT_REFERENCE,
                amount=PAYMENT_AMOUNT,
            )
            lead["Estatus"] = LeadStatus.PENDIENTE_PAGO.value
            responses.append({
                "to": phone,
                "text": f"📋 *Datos de Pago*\n\n{payment_info}",
                "type": "text",
            })

    elif action == "human_handoff":
        lead["Estatus"] = LeadStatus.HUMAN_HANDOFF.value
        responses.append({"to": phone, "text": user_message, "type": "text"})

    else:
        # action == "continue"
        responses.append({"to": phone, "text": user_message, "type": "text"})

    # ── Save assistant message to history ─────────────────────────
    _conversations[phone].append({"role": "assistant", "content": user_message})

    # ── Update Google Sheets (best effort) ────────────────────────
    _update_sheets_async(phone, lead, text, user_message)

    return jsonify({"responses": responses})


@simulator_bp.route("/api/simulator/reset", methods=["POST"])
def simulator_reset():
    """Reinicia la conversación para un número de teléfono."""
    data = request.json or {}
    phone = data.get("phone", "+525500000001")

    if phone in _conversations:
        del _conversations[phone]
    if phone in _leads:
        del _leads[phone]

    logger.info(f"Simulator conversation reset for {phone}")
    return jsonify({"status": "ok", "message": "Conversación reiniciada"})


@simulator_bp.route("/api/simulator", methods=["GET"])
def simulator_ui():
    """Sirve la interfaz de chat del simulador."""
    return send_from_directory("static", "simulator.html")


# ── Internal Helpers ──────────────────────────────────────────────

def _call_llm(
    system_prompt: str, messages: list[dict]
) -> Optional[str]:
    """Calls the OpenAI LLM with conversation history."""
    try:
        llm_messages = [{"role": "system", "content": system_prompt}]

        # Include last 20 messages for context
        for msg in messages[-20:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                llm_messages.append({"role": role, "content": content})

        response = _openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=llm_messages,
            temperature=OPENAI_TEMPERATURE,
            max_tokens=800,
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Simulator LLM call failed: {e}")
        return None


def _parse_llm_response(response: str) -> tuple[str, dict]:
    """Separa el texto del usuario del bloque JSON de acción."""
    json_pattern = r"```json\s*(.*?)\s*```"
    json_match = re.search(json_pattern, response, re.DOTALL)

    action_data = {
        "entities": {},
        "action": "continue",
        "discard_reason": None,
        "confidence": 0.5,
    }

    user_message = response

    if json_match:
        json_str = json_match.group(1)
        try:
            action_data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse LLM JSON: {json_str}")

        # Remove JSON block from user message
        user_message = re.sub(
            json_pattern, "", response, flags=re.DOTALL
        ).strip()

    # Clean up any remaining markdown artifacts
    user_message = user_message.strip("`").strip()

    return user_message, action_data


def _update_lead_entities(lead: dict, entities: dict) -> None:
    """Updates the in-memory lead with extracted entities."""
    entity_to_field = {
        "presencia_digital": "Presencia_Digital",
        "traccion_ventas": "Traccion_Ventas",
        "formalizacion": "Formalizacion",
        "uso_herramientas": "Uso_Herramientas",
    }

    for entity_key, value in entities.items():
        if value is not None:
            field = entity_to_field.get(entity_key)
            if field:
                lead[field] = value


def _calculate_score(entities: dict) -> dict:
    """Calculates the maturity score from entities."""
    try:
        return calculate_maturity_score(entities)
    except Exception as e:
        logger.warning(f"Score calculation failed: {e}")
        return {"score": 50, "nivel": "Intermedio", "desglose": {}}


def _save_lead_to_sheets(phone: str) -> None:
    """Saves a new lead to Google Sheets (best effort)."""
    try:
        lead = _leads.get(phone)
        if not lead:
            return
        sheets = SheetsClient()
        row = sheets.insert_lead(lead)
        lead["_row"] = row
        logger.info(f"Simulator: Lead saved to Sheets at row {row}")
    except Exception as e:
        logger.warning(f"Simulator: Could not save lead to Sheets: {e}")


def _update_sheets_async(
    phone: str, lead: dict, user_msg: str, bot_msg: str
) -> None:
    """Updates lead data and conversation in Google Sheets (best effort)."""
    try:
        row = lead.get("_row", -1)
        if row < 1:
            return

        sheets = SheetsClient()

        # Update entity fields
        update_fields = {}
        for field in [
            "Estatus", "Score_Madurez", "Nivel_Madurez",
            "Presencia_Digital", "Traccion_Ventas",
            "Formalizacion", "Uso_Herramientas",
        ]:
            if lead.get(field):
                update_fields[field] = lead[field]

        if update_fields:
            sheets.update_lead(row, update_fields)

        # Append conversation
        sheets.append_to_conversation(row, "user", user_msg)
        sheets.append_to_conversation(row, "assistant", bot_msg)

    except Exception as e:
        logger.warning(f"Simulator: Could not update Sheets: {e}")
