"""
API de Administración para gestionar leads y pagos.

Endpoints:
  GET  /api/admin            — Interfaz HTML del panel
  GET  /api/admin/leads      — Retorna lista de todos los leads
  POST /api/admin/leads/<row>/status — Aprueba o rechaza el pago
"""

import logging
from flask import Blueprint, request, jsonify, send_from_directory

from config import ADMIN_SECRET_KEY
from services.sheets.sheets_client import SheetsClient
from services.sheets.schema import LeadStatus, PaymentStatus

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


def _check_auth(req):
    """Verifica que la petición incluya el ADMIN_SECRET_KEY válido."""
    key = req.args.get("key") or req.headers.get("X-Admin-Key")
    return key == ADMIN_SECRET_KEY


@admin_bp.route("/api/admin", methods=["GET"])
def admin_ui():
    """Sirve la interfaz HTML del panel si la clave es correcta."""
    if not _check_auth(request):
        return "Acceso denegado. Se requiere ?key=", 403
    return send_from_directory("static", "admin.html")


@admin_bp.route("/api/admin/leads", methods=["GET"])
def get_all_leads():
    """Retorna todos los leads registrados."""
    if not _check_auth(request):
        return jsonify({"error": "Acceso denegado"}), 403

    try:
        sheets = SheetsClient()
        leads = sheets.get_all_leads()
        return jsonify({"leads": leads})
    except Exception as e:
        logger.error(f"Error fetching leads for admin: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/leads/<int:row>/status", methods=["POST"])
def update_lead_status(row):
    """
    Actualiza el estatus de pago de un lead.
    Expected JSON: {"status": "Aprobado" | "Rechazado"}
    """
    if not _check_auth(request):
        return jsonify({"error": "Acceso denegado"}), 403

    data = request.json
    if not data or "status" not in data:
        return jsonify({"error": "Missing 'status' in body"}), 400

    new_status = data["status"]
    if new_status not in [PaymentStatus.APROBADO.value, PaymentStatus.RECHAZADO.value]:
        return jsonify({"error": f"Status inválido: {new_status}"}), 400

    try:
        sheets = SheetsClient()
        update_data = {"Estatus_Pago": new_status}
        
        if new_status == PaymentStatus.APROBADO.value:
            update_data["Estatus"] = LeadStatus.APROBADO.value

        sheets.update_lead(row, update_data)
        logger.info(f"Admin actualizó fila {row} a {new_status}")
        
        return jsonify({"status": "ok", "message": f"Lead {row} actualizado a {new_status}"})
    except Exception as e:
        logger.error(f"Error updating lead status in admin: {e}")
        return jsonify({"error": str(e)}), 500
