import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from sqlmodel import select, func
from src.database.connection import get_session
from src.database.models import Usuario, Lectura, Pago, Deuda, Tarifa
from src.database.crud import get_periodo_activo_nombre

# =====================================================================
# PANTALLA DE BIENVENIDA (cuando no hay datos)
# =====================================================================
def show_welcome():
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #e0e0e0;
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
    }
    .info-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #2a5298;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-header"><h1>💧 EPSACOMUNITARIA Digital</h1><p>Sistema de Gestión Integral de Agua Potable Comunitaria</p></div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background: #e8f4fd; border-left: 5px solid #0077b6; padding: 1rem 1.5rem; border-radius: 8px; margin-bottom: 1.5rem;">
    <h4 style="margin: 0 0 0.5rem 0; color: #023e8a;">🎯 ¿Qué es EPSACOMUNITARIA Digital?</h4>
    <p style="margin: 0; color: #333; font-size: 1.05rem; line-height: 1.6;">
    <strong>EPSACOMUNITARIA Digital</strong> es una aplicación web diseñada para la <strong>gestión integral de servicios de agua potable</strong> 
    para Entidades Prestadoras de Servicios de Agua (EPSAs) a nivel de municipios, conforme a la <strong>Ley N° 2066 de Bolivia</strong>.
    </p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    features = [
        ("🏢", "Multi-EPSA", "Gestiona varias entidades desde una sola plataforma"),
        ("👥", "Usuarios", "Padrón completo de clientes y medidores"),
        ("💰", "Tarifas", "Configuración de precios por rangos de consumo"),
        ("📝", "Lecturas", "Registro manual y masivo de medidores"),
    ]
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(f"""
            <div style="background: white; padding: 0.8rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; height: 100%;">
            <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{icon}</div>
            <div style="font-weight: 700; color: #023e8a; font-size: 0.95rem;">{title}</div>
            <div style="color: #555; font-size: 0.8rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    cols2 = st.columns(4)
    features2 = [
        ("💵", "Pagos", "Cobros con generación de recibos PDF"),
        ("📊", "Deudas", "Control de morosidad y reconexiones"),
        ("🔄", "Cierres", "Cierre mensual/bimestral de facturación"),
        ("📈", "Reportes", "Recaudación, deudas y estados generales"),
    ]
    for col, (icon, title, desc) in zip(cols2, features2):
        with col:
            st.markdown(f"""
            <div style="background: white; padding: 0.8rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; height: 100%;">
            <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{icon}</div>
            <div style="font-weight: 700; color: #023e8a; font-size: 0.95rem;">{title}</div>
            <div style="color: #555; font-size: 0.8rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 ¿Cómo comenzar?")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 🔧 1. Configurar EPSA")
        st.markdown("Registra los datos básicos de tu EPSA y las tarifas de consumo.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 👥 2. Registrar Usuarios")
        st.markdown("Carga el padrón de usuarios con sus medidores y categorías.")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 📝 3. Tomar Lecturas")
        st.markdown("Registra las lecturas de los medidores para calcular consumos.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 💵 4. Gestionar Pagos")
        st.markdown("Registra pagos, genera recibos y controla la cartera.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

# =====================================================================
# DASHBOARD EJECUTIVO (cuando hay datos)
# =====================================================================
def show_executive_dashboard(epsa_id: int):
    try:
        # ----- CSS para mejorar la apariencia -----
        st.markdown("""
        <style>
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 1rem 1.2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-left: 5px solid #2a5298;
            margin-bottom: 0.5rem;
        }
        .metric-card .label {
            font-size: 0.85rem;
            color: #6c757d;
            font-weight: 500;
            letter-spacing: 0.3px;
        }
        .metric-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #1e3c72;
            line-height: 1.2;
        }
        .metric-card .sub {
            font-size: 0.75rem;
            color: #6c757d;
        }
        .alert-box {
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 0.8rem 1.2rem;
            border-radius: 8px;
            margin: 0.3rem 0;
        }
        .alert-box .alert-icon {
            font-size: 1.2rem;
            margin-right: 0.5rem;
        }
        .alert-box .alert-text {
            font-size: 0.95rem;
            color: #856404;
        }
        </style>
        """, unsafe_allow_html=True)

        # ----- OBTENER DATOS AGREGADOS -----
        with get_session() as session:
            # Usuarios totales
            total_usuarios = session.exec(
                select(func.count(Usuario.id)).where(Usuario.epsa_id == epsa_id)
            ).first()

            # Período activo
            periodo_activo = get_periodo_activo_nombre(session, epsa_id)
            if not periodo_activo:
                periodo_activo = "SIN_PERIODO"

            # Lecturas pendientes: usuarios SIN lectura en el período activo
            usuarios_con_lectura_ids = session.exec(
                select(Lectura.usuario_id)
                .distinct()
                .where(Lectura.epsa_id == epsa_id)
                .where(Lectura.periodo == periodo_activo)
            ).all()
            total_usuarios_con_lectura = len(usuarios_con_lectura_ids)
            lecturas_pendientes = total_usuarios - total_usuarios_con_lectura
            if lecturas_pendientes < 0:
                lecturas_pendientes = 0

            # Pagos del día
            hoy = datetime.now().date()
            pagos_hoy = session.exec(
                select(func.count(Pago.id))
                .where(Pago.epsa_id == epsa_id)
                .where(func.date(Pago.fecha_pago) == hoy)
            ).first() or 0

            # Morosidad (deudas pendientes)
            deudas_pendientes = session.exec(
                select(func.sum(Deuda.monto))
                .where(Deuda.epsa_id == epsa_id)
                .where(Deuda.estado == "PENDIENTE")
            ).first() or 0.0

            # RECAUDACIÓN POR PERÍODO (agrupado por periodo de facturación, no por mes calendario)
            pagos_por_periodo = session.exec(
                select(Pago.periodo, func.sum(Pago.monto))
                .where(Pago.epsa_id == epsa_id)
                .group_by(Pago.periodo)
                .order_by(func.min(Pago.fecha_pago))
            ).all()

            # CONSUMO POR PERÍODO (agrupado por periodo de facturación)
            consumo_por_periodo = session.exec(
                select(Lectura.periodo, func.sum(Lectura.consumo_m3))
                .where(Lectura.epsa_id == epsa_id)
                .where(Lectura.consumo_m3 > 0)
                .group_by(Lectura.periodo)
                .order_by(func.min(Lectura.fecha_toma))
            ).all()

            # Últimos 5 pagos + nombres de usuario precargados (evita segunda sesión)
            ultimos_pagos = session.exec(
                select(Pago)
                .where(Pago.epsa_id == epsa_id)
                .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
                .limit(5)
            ).all()

            usuario_ids = [p.usuario_id for p in ultimos_pagos]
            usuarios_nombres = {}
            if usuario_ids:
                usuarios = session.exec(
                    select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(usuario_ids))
                ).all()
                usuarios_nombres = {u.id: u.nombre for u in usuarios}

            # ---- Alertas ----
            alertas = []

            # 1. Usuarios sin lectura en período activo
            if lecturas_pendientes > 0:
                alertas.append(f"⚠️ {lecturas_pendientes} usuarios sin lectura en el período actual")

            # 2. Deudas con más de 6 meses
            deudas_antiguas = session.exec(
                select(func.count(Deuda.id))
                .where(Deuda.epsa_id == epsa_id)
                .where(Deuda.estado == "PENDIENTE")
                .where(Deuda.fecha_vencimiento <= hoy - timedelta(days=180))
            ).first() or 0
            if deudas_antiguas > 0:
                alertas.append(f"⏳ {deudas_antiguas} deudas con más de 6 meses de antigüedad")

            # 3. Tarifas vencidas
            tarifas_count = session.exec(
                select(func.count(Tarifa.id)).where(Tarifa.epsa_id == epsa_id)
            ).first() or 0
            if tarifas_count == 0:
                alertas.append("⚠️ No hay tarifas configuradas")

            # 4. Respaldo no realizado (recordatorio)
            alertas.append("💾 Recomendación: realizar respaldo de la base de datos semanalmente")

            # 5. Usuarios sin medidor
            sin_medidor = session.exec(
                select(func.count(Usuario.id))
                .where(Usuario.epsa_id == epsa_id)
                .where((Usuario.nro_medidor.is_(None)) | (Usuario.nro_medidor == ""))
            ).first() or 0
            if sin_medidor > 0:
                alertas.append(f"🔢 {sin_medidor} usuarios sin número de medidor registrado")

        # ----- METRICAS (fila 1) -----
        st.markdown("## 📊 Panel Ejecutivo")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">👥 Usuarios Activos</div>
                <div class="value">{total_usuarios}</div>
                <div class="sub">Total registrados</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #e67e22;">
                <div class="label">📝 Lecturas Pendientes</div>
                <div class="value">{lecturas_pendientes}</div>
                <div class="sub">Sin lectura en {periodo_activo}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #27ae60;">
                <div class="label">💵 Pagos del Día</div>
                <div class="value">{pagos_hoy}</div>
                <div class="sub">{hoy.strftime('%d/%m/%Y')}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #e74c3c;">
                <div class="label">📊 Morosidad (Deuda)</div>
                <div class="value">Bs {deudas_pendientes:,.2f}</div>
                <div class="sub">Pendiente de cobro</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        # ----- GRAFICOS (fila 2) -----
        col_graf1, col_graf2 = st.columns(2)

        # Gráfico 1: Recaudación por Período
        with col_graf1:
            st.subheader("📈 Recaudación por Período")
            if pagos_por_periodo:
                df_pagos = pd.DataFrame(pagos_por_periodo, columns=["periodo", "monto"])
                fig = px.bar(
                    df_pagos,
                    x="periodo",
                    y="monto",
                    labels={"periodo": "Período", "monto": "Recaudación (Bs)"},
                    text_auto=".2f",
                    color_discrete_sequence=["#2a5298"]
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=30, b=30),
                    xaxis_tickangle=-45,
                    showlegend=False
                )
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de pagos para mostrar")

        # Gráfico 2: Consumo por Período
        with col_graf2:
            st.subheader("📉 Consumo por Período (m³)")
            if consumo_por_periodo:
                df_consumo = pd.DataFrame(consumo_por_periodo, columns=["periodo", "consumo"])
                fig2 = px.bar(
                    df_consumo,
                    x="periodo",
                    y="consumo",
                    labels={"periodo": "Período", "consumo": "Consumo (m³)"},
                    text_auto=".1f",
                    color_discrete_sequence=["#27ae60"]
                )
                fig2.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=30, b=30),
                    xaxis_tickangle=-45,
                    showlegend=False
                )
                fig2.update_traces(textposition="outside")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No hay datos de consumo para mostrar")

        st.divider()
        # ----- ALERTAS (fila 3) -----
        if alertas:
            st.subheader("🚨 Alertas y Recomendaciones")
            for alerta in alertas:
                st.markdown(f"""
                <div class="alert-box">
                    <span class="alert-icon">❗</span>
                    <span class="alert-text">{alerta}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Todo en orden. No hay alertas pendientes.")

        st.divider()

        # ----- ACTIVIDAD RECIENTE (fila 4) -----
        st.subheader("🕒 Actividad Reciente")
        if ultimos_pagos:
            # Usamos usuarios_nombres precargados en la sesión principal (sin N+1)
            df_actividad = pd.DataFrame([{
                "Fecha": p.fecha_pago.strftime("%d/%m/%Y"),
                "Usuario": usuarios_nombres.get(p.usuario_id, f"ID {p.usuario_id}"),
                "Monto (Bs)": f"{p.monto:.2f}",
                "Recibo": p.recibo_nro
            } for p in ultimos_pagos])
            st.dataframe(df_actividad, use_container_width=True, hide_index=True)
        else:
            st.info("No hay pagos registrados recientemente.")

        st.divider()

        # ----- ACCESOS RAPIDOS (fila 5) -----
        st.subheader("⚡ Accesos Rápidos")
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)

        with col_a1:
            if st.button("📝 Toma de Lecturas", use_container_width=True):
                st.session_state.current_page = "toma_lecturas"
                st.rerun()

        with col_a2:
            if st.button("💵 Caja / Pagos", use_container_width=True):
                st.session_state.current_page = "caja_pagos"
                st.rerun()

        with col_a3:
            if st.button("📄 Reportes", use_container_width=True):
                st.session_state.current_page = "reportes"
                st.rerun()

        with col_a4:
            if st.button("⚙️ Configuración EPSA", use_container_width=True):
                st.session_state.current_page = "configuracion_epsa"
                st.rerun()

    except Exception as e:
        import traceback
        st.error(f"❌ Error inesperado en el dashboard ejecutivo: {e}")
        st.code(traceback.format_exc())


# =====================================================================
# FUNCIÓN PRINCIPAL DEL DASHBOARD (punto de entrada)
# =====================================================================
def show():
    epsa_id = st.session_state.get("epsa_id")
    if not epsa_id:
        show_welcome()
        return

    # Verificar si hay usuarios registrados
    with get_session() as session:
        total_usuarios = session.exec(
            select(func.count(Usuario.id)).where(Usuario.epsa_id == epsa_id)
        ).first()

    if total_usuarios == 0:
        show_welcome()
    else:
        show_executive_dashboard(epsa_id)