# src/business/limites.py
from sqlmodel import select
from src.database.connection import get_session
from src.database.models import Suscripcion, Plan, EPSA, Usuario

class LimiteExcedidoError(Exception):
    pass

def verificar_limite_usuarios(epsa_id: int):
    with get_session() as session:
        suscripcion = session.exec(
            select(Suscripcion).where(Suscripcion.epsa_id == epsa_id)
        ).first()
        
        if not suscripcion or not suscripcion.plan:
            raise LimiteExcedidoError("No hay suscripción activa")
        
        plan = suscripcion.plan
        if plan.max_usuarios == -1:
            return True  # Ilimitado
        
        # Contar usuarios actuales
        total_usuarios = session.exec(
            select(Usuario).where(Usuario.epsa_id == epsa_id)
        ).all()
        
        if len(total_usuarios) >= plan.max_usuarios:
            raise LimiteExcedidoError(
                f"Plan {plan.nombre} permite máximo {plan.max_usuarios} usuarios. "
                f"Actualmente tienes {len(total_usuarios)}."
            )
        return True

def verificar_limite_epsas(usuario_admin_id: int, total_epsas_actuales: int):
    # Lógica similar para controlar cuántas EPSAs puede crear un usuario
    pass

def calcular_precio_final(plan_id: int, descuento: int = 0) -> float:
    with get_session() as session:
        plan = session.get(Plan, plan_id)
        if not plan:
            return 0.0
        return plan.precio_mensual_usd * (1 - descuento / 100)