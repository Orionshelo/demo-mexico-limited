"""
Orquestador del Agente de IA de Mexico Limited.

Gestiona el flujo completo de la conversación con el emprendedor:
máquina de estados, invocación del LLM, extracción de entidades,
ejecución de acciones (scoring, descarte, pago, human handoff).
"""

import json
import logging
import re
from typing import Any, Optional

import openai

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    HUMAN_HANDOFF_KEYWORDS,
    PAYMENT_BANK_NAME,
    PAYMENT_ACCOUNT_NAME,
    PAYMENT_CLABE,
    PAYMENT_REFERENCE,
    PAYMENT_AMOUNT,
    CALENDLY_LINK,
    ONBOARDING_GUIDE_LINK,
    EXECUTIVE_EMAIL,
    EXECUTIVE_PHONE,
)
from agent.prompts.system_prompt import build_system_prompt
from agent.prompts.templates import build_payment_info_string
from services.sheets.sheets_client import SheetsClient
from services.sheets.schema import LeadStatus, PaymentStatus, DiscardReason
from services.whatsapp.whatsapp_client import WhatsAppClient
from services.whatsapp.payload_parser import WhatsAppMessage
from services.notifications.email_service import EmailService
from utils.scoring import calculate_maturity_score, validate_entities

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)


class AgentOrchestrator:
    """
    Máquina de estados que procesa mensajes entrantes de WhatsApp
    y ejecuta la lógica de negocio del agente.

    States:
        NUEVO → EN_TRIAJE → CALIFICADO → PENDIENTE_PAGO → APROBADO → ONBOARDING_ENVIADO
                          → DESCARTADO
                          → HUMAN_HANDOFF
    """

    def __init__(self):
        self.sheets = SheetsClient()
        self.whatsapp = WhatsAppClient()
        self.email_service = EmailService()

    async def process_message(self, message: WhatsAppMessage) -> None:
        """
        Punto de entrada principal. Procesa un mensaje entrante de WhatsApp.

        Args:
            message: Mensaje normalizado del parser.
        """
        phone = message.phone
        logger.info(f"Processing message from {phone}: type={message.message_type}")

        # Mark message as read
        if message.message_id:
            try:
                self.whatsapp.mark_as_read(message.message_id)
            except Exception as e:
                logger.warning(f"Could not mark message as read: {e}")

        # Find or create lead
        lead = self.sheets.find_lead_by_phone(phone)

        if lead is None:
            logger.info(f"Unknown phone {phone}, no matching lead found.")
            # If the lead doesn't exist in the sheet, this might be the
            # auto-generated WhatsApp message from the landing page.
            # We'll create a minimal record and start triaje.
            lead = self._create_minimal_lead(message)

        # Route based on current status
        status = lead.get("Estatus", LeadStatus.NUEVO.value)

        if status == LeadStatus.DESCARTADO.value:
            # Lead was already discarded, don't respond
            logger.info(f"Lead {phone} was discarded, ignoring message.")
            return

        if status == LeadStatus.HUMAN_HANDOFF.value:
            # Lead is in human handoff, forward message to executive
            self._notify_executive_of_message(lead, message)
            return

        if status == LeadStatus.ONBOARDING_ENVIADO.value:
            # Already onboarded, handle as general Q&A
            await self._handle_post_onboarding(lead, message)
            return

        # Handle image messages (payment receipt)
        if message.message_type == "image" and status in (
            LeadStatus.PENDIENTE_PAGO.value,
            LeadStatus.CALIFICADO.value,
        ):
            await self._handle_payment_receipt(lead, message)
            return

        # Check for explicit human handoff request
        if self._is_human_handoff_request(message.text):
            await self._handle_human_handoff(lead, message)
            return

        # Main conversation flow — invoke LLM
        await self._run_conversation(lead, message)

    # ── Core Conversation Flow ────────────────────────────────────

    async def _run_conversation(
        self, lead: dict, message: WhatsAppMessage
    ) -> None:
        """Runs the LLM conversation and processes the response."""
        phone = message.phone
        row = lead["_row"]

        # Update status to EN_TRIAJE if still NUEVO
        if lead.get("Estatus") == LeadStatus.NUEVO.value:
            self.sheets.update_lead(row, {"Estatus": LeadStatus.EN_TRIAJE.value})

        # Save user message to conversation history
        self.sheets.append_to_conversation(row, "user", message.text)

        # Build conversation history for LLM
        history = lead.get("Historial_Conversacion", [])
        if isinstance(history, str):
            try:
                history = json.loads(history)
            except json.JSONDecodeError:
                history = []

        # Add the new message
        history.append({"role": "user", "content": message.text})

        # Invoke LLM
        system_prompt = build_system_prompt(lead)
        llm_response = self._call_llm(system_prompt, history)

        if llm_response is None:
            # LLM failed, send generic response
            self.whatsapp.send_text_message(
                phone,
                "Disculpa, estoy teniendo problemas técnicos. "
                "¿Podrías repetir tu mensaje? 🙏",
            )
            return

        # Parse LLM response
        user_message, action_data = self._parse_llm_response(llm_response)

        # Save assistant message to conversation history
        self.sheets.append_to_conversation(row, "assistant", user_message)

        # Execute action
        action = action_data.get("action", "continue")

        if action == "discard":
            reason = action_data.get("discard_reason", "manual")
            self._discard_lead(lead, reason, user_message)

        elif action == "score_ready":
            entities = action_data.get("entities", {})
            self._calculate_and_update_score(lead, entities)
            # Send the conversational message
            self.whatsapp.send_text_message(phone, user_message)

        elif action == "send_payment":
            # First calculate score if not done
            entities = action_data.get("entities", {})
            if not lead.get("Score_Madurez"):
                self._calculate_and_update_score(lead, entities)
            # Send payment info
            self._send_payment_info(lead, user_message)

        elif action == "human_handoff":
            await self._handle_human_handoff(lead, message, user_message)

        else:
            # action == "continue"
            # Update entities if present
            entities = action_data.get("entities", {})
            non_null_entities = {
                k: v for k, v in entities.items() if v is not None
            }
            if non_null_entities:
                update_fields = {}
                for key, value in non_null_entities.items():
                    col_name = self._entity_to_column(key)
                    if col_name:
                        update_fields[col_name] = value
                if update_fields:
                    self.sheets.update_lead(row, update_fields)

            # Send the conversational message
            self.whatsapp.send_text_message(phone, user_message)

    # ── LLM Invocation ────────────────────────────────────────────

    def _call_llm(
        self, system_prompt: str, messages: list[dict]
    ) -> Optional[str]:
        """
        Calls the OpenAI LLM with the system prompt and conversation history.

        Returns:
            The assistant's response text, or None on failure.
        """
        try:
            llm_messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history (limit to last 20 messages)
            for msg in messages[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    llm_messages.append({"role": role, "content": content})

            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=llm_messages,
                temperature=OPENAI_TEMPERATURE,
                max_tokens=800,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    # ── Response Parsing ──────────────────────────────────────────

    def _parse_llm_response(self, response: str) -> tuple[str, dict]:
        """
        Separa el texto para el usuario del JSON de acción.

        Returns:
            Tuple of (user_visible_text, action_dict).
        """
        # Try to extract JSON block
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
            user_message = re.sub(json_pattern, "", response, flags=re.DOTALL).strip()

        # Clean up any remaining markdown artifacts
        user_message = user_message.strip("`").strip()

        return user_message, action_data

    # ── Action Handlers ───────────────────────────────────────────

    def _discard_lead(
        self, lead: dict, reason: str, farewell_message: str
    ) -> None:
        """Descarta al lead y envía mensaje de despedida."""
        row = lead["_row"]
        phone = lead.get("Telefono", "")

        # Map reason to enum
        reason_map = {
            "no_mexicano": DiscardReason.NO_MEXICANO.value,
            "multinivel": DiscardReason.MULTINIVEL.value,
            "perecedero": DiscardReason.PERECEDERO.value,
        }

        self.sheets.update_lead(
            row,
            {
                "Estatus": LeadStatus.DESCARTADO.value,
                "Razon_Descarte": reason_map.get(reason, DiscardReason.MANUAL.value),
            },
        )

        self.whatsapp.send_text_message(phone, farewell_message)
        logger.info(f"Lead {phone} discarded: {reason}")

    def _calculate_and_update_score(
        self, lead: dict, entities: dict
    ) -> None:
        """Calcula el score de madurez y actualiza Google Sheets."""
        row = lead["_row"]

        is_valid, errors = validate_entities(entities)
        if not is_valid:
            logger.warning(f"Invalid entities: {errors}")

        result = calculate_maturity_score(entities)

        self.sheets.update_lead(
            row,
            {
                "Score_Madurez": str(result["score"]),
                "Nivel_Madurez": result["nivel"],
                "Presencia_Digital": str(result["desglose"]["presencia_digital"]),
                "Traccion_Ventas": str(result["desglose"]["traccion_ventas"]),
                "Formalizacion": str(result["desglose"]["formalizacion"]),
                "Uso_Herramientas": str(result["desglose"]["uso_herramientas"]),
                "Estatus": LeadStatus.CALIFICADO.value,
            },
        )

        logger.info(
            f"Lead {lead.get('Telefono')} scored: "
            f"{result['score']} ({result['nivel']})"
        )

    def _send_payment_info(self, lead: dict, intro_message: str) -> None:
        """Envía la información de pago al lead."""
        row = lead["_row"]
        phone = lead.get("Telefono", "")
        name = lead.get("Nombre", "Emprendedor")

        # Build payment string
        payment_info = build_payment_info_string(
            bank_name=PAYMENT_BANK_NAME,
            account_name=PAYMENT_ACCOUNT_NAME,
            clabe=PAYMENT_CLABE,
            reference=PAYMENT_REFERENCE,
            amount=PAYMENT_AMOUNT,
        )

        # Send intro message first (the conversational part)
        if intro_message:
            self.whatsapp.send_text_message(phone, intro_message)

        # Then send the official template with payment data
        self.whatsapp.send_payment_template(
            to=phone, name=name, payment_info=payment_info
        )

        # Update status
        self.sheets.update_lead(
            row, {"Estatus": LeadStatus.PENDIENTE_PAGO.value}
        )

        logger.info(f"Payment info sent to {phone}")

    async def _handle_payment_receipt(
        self, lead: dict, message: WhatsAppMessage
    ) -> None:
        """Procesa un comprobante de pago (imagen) enviado por el lead."""
        row = lead["_row"]
        phone = lead.get("Telefono", "")
        name = lead.get("Nombre", "Emprendedor")

        # Download the image
        image_data = None
        if message.media_id:
            image_data = self.whatsapp.download_media(message.media_id)

        # Update status
        self.sheets.update_lead(
            row,
            {
                "Estatus_Pago": PaymentStatus.COMPROBANTE_ENVIADO.value,
                "Notas_Agente": f"Comprobante recibido - media_id: {message.media_id}",
            },
        )

        # Send to executive for validation
        if image_data:
            self.email_service.send_payment_receipt(
                lead_name=name,
                lead_phone=phone,
                lead_email=lead.get("Correo", ""),
                lead_company=lead.get("Empresa", ""),
                image_data=image_data,
                mime_type=message.media_mime_type or "image/jpeg",
            )

        # Confirm receipt to user
        self.whatsapp.send_text_message(
            phone,
            f"¡Gracias, {name}! He recibido tu comprobante. 📄\n\n"
            "Nuestro equipo lo validará y te confirmaremos tu acceso "
            "en un plazo máximo de 24 horas. ¡Estamos emocionados de "
            "que formes parte de Mexico Limited! 🇲🇽🚀",
        )

        logger.info(f"Payment receipt received from {phone}")

    async def _handle_human_handoff(
        self,
        lead: dict,
        message: WhatsAppMessage,
        custom_message: str = None,
    ) -> None:
        """Activa el human handoff y notifica al ejecutivo."""
        row = lead["_row"]
        phone = lead.get("Telefono", "")
        name = lead.get("Nombre", "Emprendedor")

        # Update status
        self.sheets.update_lead(
            row, {"Estatus": LeadStatus.HUMAN_HANDOFF.value}
        )

        # Send message to user
        handoff_msg = custom_message or (
            f"Entiendo, {name}. Voy a conectarte con uno de nuestros "
            f"ejecutivos para que te atienda personalmente. "
            f"Te contactarán en breve. 🤝"
        )
        self.whatsapp.send_text_message(phone, handoff_msg)

        # Notify executive
        self.email_service.send_handoff_alert(
            lead_name=name,
            lead_phone=phone,
            lead_company=lead.get("Empresa", ""),
            conversation_summary=message.text,
        )

        logger.info(f"Human handoff activated for {phone}")

    async def _handle_post_onboarding(
        self, lead: dict, message: WhatsAppMessage
    ) -> None:
        """Handles messages from already-onboarded leads."""
        phone = lead.get("Telefono", "")
        name = lead.get("Nombre", "")

        # Simple response directing them to support
        self.whatsapp.send_text_message(
            phone,
            f"¡Hola, {name}! Ya eres parte de Mexico Limited. 🎉\n\n"
            "Si tienes alguna pregunta o necesitas ayuda, puedes "
            "escribirnos y un ejecutivo te atenderá. "
            "También puedes revisar tu guía de onboarding y "
            f"agendar una llamada aquí: {CALENDLY_LINK}",
        )

    # ── Helpers ───────────────────────────────────────────────────

    def _create_minimal_lead(self, message: WhatsAppMessage) -> dict:
        """Creates a minimal lead record from an incoming WhatsApp message."""
        lead_data = {
            "Nombre": message.display_name or "Desconocido",
            "Telefono": message.phone,
            "Estatus": LeadStatus.NUEVO.value,
        }

        row = self.sheets.insert_lead(lead_data)
        lead_data["_row"] = row
        return lead_data

    def _is_human_handoff_request(self, text: str) -> bool:
        """Checks if the user message explicitly requests human assistance."""
        if not text:
            return False
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in HUMAN_HANDOFF_KEYWORDS)

    def _notify_executive_of_message(
        self, lead: dict, message: WhatsAppMessage
    ) -> None:
        """Forwards a message from a handoff-lead to the executive."""
        self.email_service.send_handoff_alert(
            lead_name=lead.get("Nombre", ""),
            lead_phone=lead.get("Telefono", ""),
            lead_company=lead.get("Empresa", ""),
            conversation_summary=f"[Nuevo mensaje]: {message.text}",
        )

    @staticmethod
    def _entity_to_column(entity_key: str) -> Optional[str]:
        """Maps entity key names to Google Sheets column names."""
        mapping = {
            "presencia_digital": "Presencia_Digital",
            "traccion_ventas": "Traccion_Ventas",
            "formalizacion": "Formalizacion",
            "uso_herramientas": "Uso_Herramientas",
        }
        return mapping.get(entity_key)


# ── Module-level singleton ────────────────────────────────────────

_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Returns the singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
