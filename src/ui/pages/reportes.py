import streamlit as st
from datetime import date, timedelta
from sqlmodel import select, func
import pandas as pd
import io
from src.database.connection import get_session
from src.database.models import EPSA, Usuario, Lectura, Pago, Deuda, Periodo, ConfiguracionEPSA, Tarifa
from src.database.crud import get_periodo_activo_nombre
from src.utils.recibo_pdf import generar_recibo_pdf


def show():
    st.title("📄 Reportes")

    epsa_id = st.session_state.get("epsa_id")
    if not epsa_id:
        st.warning("⚠️ Primero selecciona una EPSA en el panel lateral.")
        return

    # Cargar datos de la EPSA activa
    with get_session() as session:
        epsa = session.get(EPSA, epsa_id)
        epsa_nombre = epsa.nombre if epsa else "EPSA Desconocida"

    st.info(f"📊 EPSA: **{epsa_nombre}**")

    # ------------------------------------------------------------------
    # PESTAÑAS DE REPORTES
    # ------------------------------------------------------------------
    tab_recaudacion, tab_cliente, tab_deudas, tab_general = st.tabs([
        "💰 Recaudación por Fecha",
        "👤 Recaudación por Cliente", 
        "📋 Deudas Pendientes",
        "📈 Reporte General"
    ])

    # ==================================================================
    # TAB 1: RECAUDACIÓN POR FECHA
    # ==================================================================
    with tab_recaudacion:
        st.subheader("💰 Recaudación por Rango de Fechas")

        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio", value=date.today() - timedelta(days=30), key="rep_fec_ini")
        with col2:
            fecha_fin = st.date_input("Fecha fin", value=date.today(), key="rep_fec_fin")

        if st.button("📊 Generar Reporte", type="primary", key="btn_recaudacion"):
            with get_session() as session:
                pagos = session.exec(
                    select(Pago, Usuario)
                    .join(Usuario, Pago.usuario_id == Usuario.id)
                    .where(Pago.epsa_id == epsa_id)
                    .where(Pago.fecha_pago >= fecha_inicio)
                    .where(Pago.fecha_pago <= fecha_fin)
                    .order_by(Pago.fecha_pago.desc())
                ).all()

                if not pagos:
                    st.info("No hay pagos registrados en este rango de fechas.")
                else:
                    data = []
                    total_recaudado = 0.0
                    for pago, usuario in pagos:
                        data.append({
                            "Recibo N°": pago.recibo_nro,
                            "Fecha": pago.fecha_pago.strftime("%d/%m/%Y"),
                            "Código": usuario.codigo,
                            "Nombre": usuario.nombre,
                            "Período": pago.periodo,
                            "Monto (Bs)": f"{pago.monto:.2f}"
                        })
                        total_recaudado += pago.monto

                    st.dataframe(data, use_container_width=True, hide_index=True)
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Total Recaudado", f"{total_recaudado:.2f} Bs")
                    col_m2.metric("N° Transacciones", len(pagos))
                    col_m3.metric("Promedio", f"{total_recaudado/len(pagos):.2f} Bs")

                    # CORRECCIÓN: Exportar a Excel usando BytesIO
                    df = pd.DataFrame(data)
                    excel_buffer = io.BytesIO()
                    df.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)
                    
                    st.download_button(
                        "📥 Descargar Excel",
                        data=excel_buffer,
                        file_name=f"recaudacion_{fecha_inicio}_{fecha_fin}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    # ==================================================================
    # TAB 2: RECAUDACIÓN POR CLIENTE
    # ==================================================================
    with tab_cliente:
        st.subheader("👤 Historial de Pagos por Cliente")

        search_term = st.text_input("Buscar por código o nombre", placeholder="Ej: AP-001 o GONZALES", key="rep_search_cliente")
        
        if search_term:
            with get_session() as session:
                usuarios = session.exec(
                    select(Usuario)
                    .where(Usuario.epsa_id == epsa_id)
                    .where(
                        (func.upper(Usuario.codigo).contains(search_term.upper())) |
                        (func.upper(Usuario.nombre).contains(search_term.upper()))
                    )
                ).all()

            if not usuarios:
                st.warning("No se encontraron usuarios.")
            else:
                opciones = {f"{u.codigo} | {u.nombre} | {u.zona}": u.id for u in usuarios}
                seleccion = st.selectbox("Seleccione cliente", list(opciones.keys()), key="rep_sel_cliente")
                usuario_id = opciones[seleccion]

                with get_session() as session:
                    usuario = session.get(Usuario, usuario_id)
                    usuario_nombre = usuario.nombre
                    usuario_codigo = usuario.codigo

                    pagos = session.exec(
                        select(Pago)
                        .where(Pago.usuario_id == usuario_id)
                        .order_by(Pago.fecha_pago.desc())
                    ).all()

                    deudas = session.exec(
                        select(Deuda)
                        .where(Deuda.usuario_id == usuario_id)
                        .order_by(Deuda.id.desc())
                    ).all()

                st.markdown(f"**Cliente:** {usuario_codigo} - {usuario_nombre}")

                st.markdown("#### 💰 Pagos Realizados")
                if pagos:
                    data_pagos = []
                    total_pagado = 0.0
                    for p in pagos:
                        data_pagos.append({
                            "Recibo N°": p.recibo_nro,
                            "Fecha": p.fecha_pago.strftime("%d/%m/%Y"),
                            "Período": p.periodo,
                            "Monto (Bs)": f"{p.monto:.2f}"
                        })
                        total_pagado += p.monto
                    
                    st.dataframe(data_pagos, use_container_width=True, hide_index=True)
                    st.metric("Total Pagado", f"{total_pagado:.2f} Bs")
                else:
                    st.info("No tiene pagos registrados.")

                st.markdown("#### 📋 Deudas")
                if deudas:
                    data_deudas = []
                    total_deuda = 0.0
                    total_pendiente = 0.0
                    for d in deudas:
                        data_deudas.append({
                            "N° Deuda": d.nro_deuda,
                            "Período": d.periodo,
                            "Monto (Bs)": f"{d.monto:.2f}",
                            "Estado": d.estado,
                            "Vencimiento": d.fecha_vencimiento.strftime("%d/%m/%Y") if d.fecha_vencimiento else "-"
                        })
                        total_deuda += d.monto
                        if d.estado == "PENDIENTE":
                            total_pendiente += d.monto
                    
                    st.dataframe(data_deudas, use_container_width=True, hide_index=True)
                    col_d1, col_d2 = st.columns(2)
                    col_d1.metric("Total Deudas", f"{total_deuda:.2f} Bs")
                    col_d2.metric("Pendiente", f"{total_pendiente:.2f} Bs", delta=f"-{total_deuda - total_pendiente:.2f} Pagado")
                else:
                    st.info("No tiene deudas registradas.")

                st.markdown("#### 📊 Resumen de Cuenta")
                saldo = usuario.saldo_actual
                st.metric("Saldo Actual (Deuda acumulada)", f"{saldo:.2f} Bs",
                         delta="Al día" if saldo <= 0 else "Debe")

    # ==================================================================
    # TAB 3: DEUDAS PENDIENTES
    # ==================================================================
    with tab_deudas:
        st.subheader("📋 Planilla de Deudas Pendientes")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_periodo = st.text_input("Filtrar por período (opcional)", placeholder="Ej: ENERO - 2024")
        with col_f2:
            solo_mayores = st.number_input("Solo deudas mayores a (Bs)", min_value=0.0, value=0.0, step=10.0)

        if st.button("📋 Generar Planilla", type="primary", key="btn_deudas"):
            with get_session() as session:
                query = select(Deuda, Usuario).join(Usuario, Deuda.usuario_id == Usuario.id).where(
                    Deuda.epsa_id == epsa_id,
                    Deuda.estado == "PENDIENTE"
                )
                
                if filtro_periodo:
                    query = query.where(Deuda.periodo.contains(filtro_periodo.upper()))
                
                deudas = session.exec(query.order_by(Deuda.periodo, Usuario.codigo)).all()

                if not deudas:
                    st.info("No hay deudas pendientes con los filtros aplicados.")
                else:
                    data = []
                    total_deuda = 0.0
                    for deuda, usuario in deudas:
                        if deuda.monto < solo_mayores:
                            continue
                        data.append({
                            "N° Deuda": deuda.nro_deuda,
                            "Código": usuario.codigo,
                            "Nombre": usuario.nombre,
                            "Zona": usuario.zona,
                            "Período": deuda.periodo,
                            "Consumo (m³)": f"{deuda.consumo_m3:.2f}" if deuda.consumo_m3 else "-",
                            "Monto (Bs)": f"{deuda.monto:.2f}",
                            "Vencimiento": deuda.fecha_vencimiento.strftime("%d/%m/%Y") if deuda.fecha_vencimiento else "-"
                        })
                        total_deuda += deuda.monto

                    st.dataframe(data, use_container_width=True, hide_index=True)
                    st.metric("Total Deuda Pendiente", f"{total_deuda:.2f} Bs", delta=f"{len(data)} deudas")

                    # CORRECCIÓN: Exportar con BytesIO
                    if data:
                        df = pd.DataFrame(data)
                        excel_buffer = io.BytesIO()
                        df.to_excel(excel_buffer, index=False, engine='openpyxl')
                        excel_buffer.seek(0)
                        
                        st.download_button(
                            "📥 Descargar Excel",
                            data=excel_buffer,
                            file_name=f"deudas_pendientes_{date.today()}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

    # ==================================================================
    # TAB 4: REPORTE GENERAL
    # ==================================================================
    with tab_general:
        st.subheader("📈 Reporte General de la EPSA")
        st.markdown("Resumen ejecutivo de la situación actual")

        with get_session() as session:
            periodo_activo = get_periodo_activo_nombre(session, epsa_id)

        st.info(f"📅 Período activo: **{periodo_activo}**")

        if st.button("📊 Generar Reporte General", type="primary", key="btn_general"):
            with get_session() as session:
                # Métricas de usuarios
                total_usuarios = session.exec(
                    select(func.count(Usuario.id)).where(Usuario.epsa_id == epsa_id)
                ).first() or 0

                # Lecturas del periodo
                lecturas_periodo = session.exec(
                    select(Lectura).where(
                        Lectura.epsa_id == epsa_id,
                        Lectura.periodo == periodo_activo
                    )
                ).all()
                total_lecturas = len(lecturas_periodo)
                usuarios_sin_lectura = total_usuarios - total_lecturas

                # Pagos del periodo
                pagos_periodo = session.exec(
                    select(Pago).where(
                        Pago.epsa_id == epsa_id,
                        Pago.periodo == periodo_activo
                    )
                ).all()
                total_pagado_periodo = sum(p.monto for p in pagos_periodo)
                usuarios_pagados = len(pagos_periodo)
                usuarios_pendientes = total_lecturas - usuarios_pagados

                # Deudas
                deudas_pendientes = session.exec(
                    select(Deuda).where(
                        Deuda.epsa_id == epsa_id,
                        Deuda.estado == "PENDIENTE"
                    )
                ).all()
                total_deuda_pendiente = sum(d.monto for d in deudas_pendientes)
                usuarios_con_deuda = len(set(d.usuario_id for d in deudas_pendientes))

                # Histórico
                total_recaudado_historico = session.exec(
                    select(func.sum(Pago.monto)).where(Pago.epsa_id == epsa_id)
                ).first() or 0.0

                # Tarifas
                tarifas = session.exec(
                    select(Tarifa).where(Tarifa.epsa_id == epsa_id).order_by(Tarifa.orden)
                ).all()

            # Mostrar métricas
            st.markdown("### 👥 Usuarios")
            col_u1, col_u2, col_u3 = st.columns(3)
            col_u1.metric("Total Usuarios", total_usuarios)
            col_u2.metric("Con Lectura", total_lecturas)
            col_u3.metric("Sin Lectura", max(0, usuarios_sin_lectura))

            st.markdown("### 💰 Situación del Período Actual")
            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.metric("Pagados", usuarios_pagados)
            col_p2.metric("Pendientes", max(0, usuarios_pendientes))
            col_p3.metric("Recaudado", f"{total_pagado_periodo:.2f} Bs")

            st.markdown("### 📋 Deudas Acumuladas")
            col_d1, col_d2, col_d3 = st.columns(3)
            col_d1.metric("Total Deuda", f"{total_deuda_pendiente:.2f} Bs")
            col_d2.metric("Usuarios con Deuda", usuarios_con_deuda)
            col_d3.metric("Recaudado Histórico", f"{total_recaudado_historico:.2f} Bs")

            # Gráfico
            if total_lecturas > 0 or usuarios_sin_lectura > 0:
                st.markdown("### 📊 Estado de Pagos del Período")
                chart_data = pd.DataFrame({
                    'Estado': ['Pagados', 'Pendientes', 'Sin Lectura'],
                    'Cantidad': [usuarios_pagados, max(0, usuarios_pendientes), max(0, usuarios_sin_lectura)]
                })
                st.bar_chart(chart_data.set_index('Estado'))

            # Tarifas
            if tarifas:
                st.markdown("### 💧 Tarifas Vigentes")
                data_tarifas = []
                for t in tarifas:
                    rango_fin = f"{t.rango_fin:.2f}" if t.rango_fin else "∞"
                    data_tarifas.append({
                        "Orden": t.orden,
                        "Rango": f"{t.rango_inicio:.2f} - {rango_fin} m³",
                        "Precio Unitario": f"{t.precio_unitario:.2f} Bs",
                        "Cargo Fijo": f"{t.cargo_fijo:.2f} Bs"
                    })
                st.dataframe(data_tarifas, use_container_width=True, hide_index=True)

            # Exportar resumen
            resumen = {
                "EPSA": epsa_nombre,
                "Periodo Activo": periodo_activo,
                "Total Usuarios": total_usuarios,
                "Total Recaudado Historico": total_recaudado_historico,
                "Total Deuda Pendiente": total_deuda_pendiente,
                "Usuarios con Deuda": usuarios_con_deuda,
                "Fecha Reporte": date.today().strftime("%d/%m/%Y")
            }
            df_resumen = pd.DataFrame([resumen])
            
            # CORRECCIÓN: Exportar con BytesIO
            excel_buffer = io.BytesIO()
            df_resumen.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            
            st.download_button(
                "📥 Descargar Resumen Excel",
                data=excel_buffer,
                file_name=f"reporte_general_{epsa_nombre.replace(' ', '_')}_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )