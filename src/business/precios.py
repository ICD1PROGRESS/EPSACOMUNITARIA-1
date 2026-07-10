# src/business/precios.py
from datetime import date

def calcular_precio(plan_precio: float, municipio_habitantes: int, 
                    es_migracion_excel: bool = False, 
                    es_pago_anual: bool = False,
                    referido: bool = False) -> dict:
    
    descuento = 0
    motivos = []
    
    # 30% descuento para municipios < 5,000 habitantes
    if municipio_habitantes < 5000:
        descuento = max(descuento, 30)
        motivos.append("Programa digitalización rural (-30%)")
    
    # 16 % de descuento efectivo por 2 años de suscripcion
    if es_pago_anual:
        descuento = max(descuento, 16.0)
        motivos.append("Pago por 2 años: descuento (-16%)")
    
    # Migración desde Excel: implementación gratuita
    # (esto se aplica al servicio de implementación, no al plan mensual)
    
    precio_final = plan_precio * (1 - descuento / 100)
    
    return {
        "precio_original": plan_precio,
        "descuento_porcentaje": descuento,
        "precio_final": round(precio_final, 2),
        "motivos": motivos,
        "implementacion_gratis": es_migracion_excel
    }