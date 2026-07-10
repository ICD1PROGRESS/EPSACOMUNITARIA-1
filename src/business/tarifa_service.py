from sqlmodel import Session
from src.database.crud import get_tarifas_by_epsa
from src.database.models import Tarifa
from typing import List

def calcular_importe_consumo(consumo_m3: float, tarifas: List[Tarifa]) -> float:
    """
    Calcula el importe según rangos progresivos.
    El primer rango debe tener cargo_fijo > 0.
    """
    if not tarifas:
        return 0.0

    # Ordenar por rango_inicio ascendente
    tarifas_ordenadas = sorted(tarifas, key=lambda x: x.rango_inicio)
    importe_total = 0.0
    consumo_restante = consumo_m3

    for i, t in enumerate(tarifas_ordenadas):
        # Determinar límite superior de este rango
        if t.rango_fin is None:
            limite = consumo_restante
        else:
            limite = min(t.rango_fin - t.rango_inicio, consumo_restante)
            if limite < 0:
                continue

        if limite > 0:
            importe_total += limite * t.precio_unitario

        # Aplicar cargo fijo solo al primer rango
        if i == 0 and t.cargo_fijo > 0:
            importe_total += t.cargo_fijo

        consumo_restante -= limite
        if consumo_restante <= 0:
            break

    return round(importe_total, 2)
    
# Ejemplo de uso desde una lectura:
def calcular_importe_lectura(session: Session, epsa_id: int, consumo_m3: float) -> float:
    tarifas = get_tarifas_by_epsa(session, epsa_id)
    return calcular_importe_consumo(consumo_m3, tarifas)