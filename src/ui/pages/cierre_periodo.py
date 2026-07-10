import streamlit as st
from datetime import date
from sqlmodel import select
from src.database.connection import get_session
from src.database.models import Lectura, Periodo
from src.database.crud import (
    get_periodo_activo_nombre,
    get_lecturas_periodo_detalle,
    ejecutar_cierre_periodo,
    get_tarifas_by_epsa
)
from src.business.tarifa_service import calcular_importe_consumo


def show():
    st.title("🔄 Cierre de Período")
    st.caption("Sistema de Gestión Integral de Agua Potable Comunitaria")

    epsa_id = st.session_state.get("epsa_id")
    if not epsa_id:
        st.warning("⚠️ Primero selecciona una EPSA en el panel lateral.")
        return

    # ------------------------------------------------------------------
    # MENSAJES FLASH
    # ------------------------------------------------------------------
    if "cierre_mensaje" in st.session_state:
        msg = st.session_state.cierre_mensaje
        if msg["tipo"] == "success":
            st.success(msg["texto"])
        elif msg["tipo"] == "error":
            st.error(msg["texto"])
        del st.session_state.cierre_mensaje

    # ------------------------------------------------------------------
    # PERIODO ACTIVO
    # ------------------------------------------------------------------
    with get_session() as session:
        periodo_actual = get_periodo_activo_nombre(session, epsa_id)

    st.info(f"📅 Período activo: **{periodo_actual}**")

    # ------------------------------------------------------------------
    # PASO 1: CONTABILIZACIÓN (equivalente a actua2_Click)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 Paso 1: Contabilización y Vista Previa")

    with get_session() as session:
        detalle = get_lecturas_periodo_detalle(session, epsa_id, periodo_actual)
        tarifas = get_tarifas_by_epsa(session, epsa_id)

    if not detalle:
        st.warning("No hay lecturas registradas para este período. Ve a '📝 Toma de Lecturas' primero.")
        return

    # Botón recalcular (por si cambiaron tarifas o lecturas)
    col_rec1, col_rec2 = st.columns([1, 3])
    with col_rec1:
        if st.button("🔄 Recalcular Tarifas", type="secondary"):
            with get_session() as session:
                lecturas = session.exec(
                    select(Lectura).where(
                        Lectura.epsa_id == epsa_id,
                        Lectura.periodo == periodo_actual
                    )
                ).all()
                for lect in lecturas:
                    consumo = lect.lectura_actual - lect.lectura_anterior
                    if consumo < 0:
                        consumo = 0
                    lect.consumo_m3 = round(consumo, 2)
                    if tarifas:
                        lect.importe_calculado = calcular_importe_consumo(consumo, tarifas)
                    else:
                        lect.importe_calculado = 0.0
                    session.add(lect)
                session.commit()
            st.success("Tarifas recalculadas para todas las lecturas del período.")
            st.rerun()

    with col_rec2:
        if not tarifas:
            st.error("⚠️ No hay tarifas configuradas. Los importes serán 0. Ve a '💰 Tarifas'.")

    # Tabla estilo hoja "base" del macro

    df_data = []
    for d in detalle:
        df_data.append({
            "Código": d["codigo"],
            "Nombre": d["nombre"],
            "Lect. Ant.": f"{d['lectura_anterior']:.2f}",
            "Lect. Act.": f"{d['lectura_actual']:.2f}",
            "Consumo": f"{d['consumo_m3']:.2f}",
            "Importe (Bs)": f"{d['importe_calculado']:.2f}",
            "Deuda Ant. (Bs)": f"{d['deuda_anterior']:.2f}",
            "Total (Bs)": f"{d['total']:.2f}",
            "Estado": "✅ PAGADO" if d["pagado"] else "⏳ PENDIENTE"
        })

    st.dataframe(df_data, use_container_width=True, hide_index=True)

    # Métricas resumen
    total_pagados = sum(1 for d in detalle if d["pagado"])
    total_pendientes = len(detalle) - total_pagados
    total_importe = sum(d["importe_calculado"] for d in detalle)
    total_deuda = sum(d["deuda_anterior"] for d in detalle)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Usuarios con lectura", len(detalle))
    c2.metric("Pagados", total_pagados)
    c3.metric("Pendientes", total_pendientes)
    c4.metric("Importe Total Período", f"{total_importe:.2f} Bs")

    # ------------------------------------------------------------------
    # PASO 2: CIERRE DEFINITIVO (equivalente a actua3_Click)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔒 Paso 2: Cierre Definitivo del Período")
    st.markdown("""
    - Pasa lectura actual → lectura anterior (automático en la próxima toma)
    - Genera registros  **Deuda** para los que NO pagaron
    - Actualiza saldo acumulado del usuario (columna K)
    - Cierra período actual y crea el siguiente
    - Limpia datos temporales del período cerrado
    """)

    st.warning("⚠️ **ATENCIÓN:** Esta acción es irreversible. Asegúrate de haber contabilizado todas las lecturas.")

    with st.form("form_cierre"):
        st.markdown("**Definir nuevo período** (equivalente a `defper_Click` + `Lperiodo`)")

        # Sugerencia de nombre
        mes_actual = date.today().strftime("%B").upper()
        anio_actual = date.today().year
        sugerencia = f"{mes_actual} - {anio_actual}"

        nuevo_periodo = st.text_input(
            "Nombre del nuevo período activo",
            value=sugerencia,
            placeholder="Ej: ENERO - 2024"
        )

        st.markdown("""
        **Resumen de lo que ocurrirá:**
        1. Se generarán deudas en la tabla **Deuda** para usuarios con estado **PENDIENTE**
        2. Se sumará el importe al **saldo acumulado** de cada usuario con deuda
        3. Se marcará el período actual como **CERRADO**
        4. Se creará el nuevo período para registrar lecturas
        """)

        confirmar = st.checkbox("✅ Confirmo que he revisado la contabilización y deseo cerrar el período")

        submitted = st.form_submit_button("🔴 EJECUTAR CIERRE DE PERÍODO", type="primary", use_container_width=True)

        if submitted:
            if not confirmar:
                st.error("❌ Debes marcar la casilla de confirmación para proceder.")
            elif not nuevo_periodo:
                st.error("❌ Debes ingresar el nombre del nuevo período.")
            else:
                try:
                    with get_session() as session:
                        # Verificar que no exista ya
                        existente = session.exec(
                            select(Periodo).where(
                                Periodo.epsa_id == epsa_id,
                                Periodo.nombre == nuevo_periodo
                            )
                        ).first()
                        if existente:
                            st.error(f"El período '{nuevo_periodo}' ya existe. Use otro nombre.")
                            return

                        resumen = ejecutar_cierre_periodo(
                            session, epsa_id, periodo_actual, nuevo_periodo
                        )

                    texto = (
                        f"✅ **Período '{periodo_actual}' cerrado exitosamente.**\n\n"
                        f"📊 **Resumen del cierre:**\n"
                        f"- Lecturas procesadas: **{resumen['lecturas_procesadas']}**\n"
                        f"- Deudas generadas (no pagados): **{resumen['deudas_generadas']}**\n"
                        f"- Usuarios al día (pagados): **{resumen['deudas_pagadas']}**\n"
                        f"- Nuevo período creado: **{resumen['nuevo_periodo']}**\n\n"
                        f"📝 Ahora puede ir a **📝 Toma de Lecturas** para registrar el nuevo período."
                    )

                    st.session_state.cierre_mensaje = {
                        "tipo": "success",
                        "texto": texto
                    }
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error durante el cierre: {e}")