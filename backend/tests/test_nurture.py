"""
Tests para la lógica de nurturing (seguimiento) de leads.

La lógica es pura (sin I/O): dada la fila del lead y la hora actual,
decide si toca enviar un mensaje de seguimiento y por qué canal.
"""

import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.nurture import decide_nurture_action, NurtureAction, NURTURE_TRACKS


NOW = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)


def hours_ago(h: float) -> str:
    return (NOW - timedelta(hours=h)).isoformat()


def make_lead(
    status="Nuevo",
    registro="",
    ultimo_nurture="",
    etapa="",
    nombre="Ana",
    correo="ana@example.com",
):
    return {
        "Nombre": nombre,
        "Correo": correo,
        "Telefono": "+5215500000000",
        "Empresa": "Artesanías Ana",
        "Estatus": status,
        "Fecha_Registro": registro,
        "Ultimo_Nurture": ultimo_nurture,
        "Nurture_Etapa": etapa,
    }


class TestTrackSelection:
    """Solo ciertos estatus deben entrar en una secuencia de nurturing."""

    def test_estatus_no_elegibles_devuelven_none(self):
        for status in [
            "Calificado",
            "Descartado",
            "Human Handoff",
            "En Triaje",
            "Aprobado",
            "Onboarding Enviado",
        ]:
            lead = make_lead(status=status, registro=hours_ago(500))
            assert decide_nurture_action(lead, NOW) is None, status

    def test_nuevo_es_elegible(self):
        lead = make_lead(status="Nuevo", registro=hours_ago(30))
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert action.track == "sin_respuesta"

    def test_pendiente_pago_es_elegible(self):
        lead = make_lead(status="Pendiente Pago", registro=hours_ago(30))
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert action.track == "pago_pendiente"


class TestAnchorAndTiming:
    def test_sin_anchor_devuelve_none(self):
        lead = make_lead(status="Nuevo", registro="")
        assert decide_nurture_action(lead, NOW) is None

    def test_anchor_invalido_devuelve_none(self):
        lead = make_lead(status="Nuevo", registro="no-es-fecha")
        assert decide_nurture_action(lead, NOW) is None

    def test_antes_de_la_cadencia_devuelve_none(self):
        # Etapa 0, solo 10h desde el registro; la etapa 1 requiere 24h.
        lead = make_lead(status="Nuevo", registro=hours_ago(10))
        assert decide_nurture_action(lead, NOW) is None

    def test_primera_etapa_al_cumplir_cadencia(self):
        lead = make_lead(status="Nuevo", registro=hours_ago(30))
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert action.stage == 1
        assert "whatsapp" in action.channels

    def test_usa_ultimo_nurture_sobre_registro(self):
        # Registro muy viejo, pero el último nurture fue hace 10h:
        # la etapa 2 requiere más tiempo, así que aún no toca.
        lead = make_lead(
            status="Nuevo",
            registro=hours_ago(500),
            ultimo_nurture=hours_ago(10),
            etapa="1",
        )
        assert decide_nurture_action(lead, NOW) is None

    def test_segunda_etapa_al_cumplir_cadencia(self):
        lead = make_lead(
            status="Nuevo",
            registro=hours_ago(500),
            ultimo_nurture=hours_ago(50),  # etapa 2 requiere 48h
            etapa="1",
        )
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert action.stage == 2

    def test_cap_de_etapas_detiene_secuencia(self):
        max_stages = NURTURE_TRACKS["sin_respuesta"]["max_stages"]
        lead = make_lead(
            status="Nuevo",
            registro=hours_ago(500),
            ultimo_nurture=hours_ago(500),
            etapa=str(max_stages),
        )
        assert decide_nurture_action(lead, NOW) is None


class TestChannelsAndContent:
    def test_segunda_etapa_incluye_email(self):
        lead = make_lead(
            status="Nuevo",
            ultimo_nurture=hours_ago(50),
            etapa="1",
        )
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert "email" in action.channels
        assert action.email_subject
        assert action.email_html

    def test_whatsapp_text_incluye_nombre(self):
        lead = make_lead(status="Nuevo", registro=hours_ago(30), nombre="Beto")
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert "Beto" in action.whatsapp_text

    def test_pago_pendiente_progresa_de_etapa(self):
        lead = make_lead(
            status="Pendiente Pago",
            ultimo_nurture=hours_ago(80),  # etapa 2 pago requiere 72h
            etapa="1",
        )
        action = decide_nurture_action(lead, NOW)
        assert action is not None
        assert action.track == "pago_pendiente"
        assert action.stage == 2
