# src/ui/pages/administracion.py
import streamlit as st
from sqlmodel import select
from datetime import date, timedelta
from src.database.connection import get_session
from src.database.models import (
    Suscripcion, Plan, EPSA, EstadoSuscripcion, UsuarioSistema
)
from src.utils.auth import (requerir_rol, crear_usuario_sistema, listar_usuarios_sistema, cambiar_estado_usuario, reset_password)
from src.database.crud import get_all_epsas


def show():
    # Solo super_admin puede acceder
    requerir_rol(["super_admin"])    
    st.title("🛠️ Panel de Administración")
    st.caption("Gestión integral de suscripciones, planes y usuarios del sistema")

    # ============================================================
    # PESTAÑAS PRINCIPALES
    # ============================================================
    tab_suscripciones, tab_planes, tab_usuarios = st.tabs([
        "📋 Suscripciones",
        "💰 Planes",
        "👤 Usuarios del Sistema"
    ])

    # ==================================================================
    with tab_suscripciones:
        _mostrar_suscripciones()

    with tab_planes:
        _mostrar_planes()

    with tab_usuarios:
        _mostrar_usuarios_sistema()

# ============================================================
# SECCIÓN: SUSCRIPCIONES
# ============================================================
def _mostrar_suscripciones():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Suscripciones existentes")
        with get_session() as session:
            suscripciones = session.exec(select(Suscripcion)).all()
            
            if not suscripciones:
                data = []
            else:
                # PRECARGA: evita N+1. Una sola query para EPSAs y Planes
                epsa_ids = {s.epsa_id for s in suscripciones}
                plan_ids = {s.plan_id for s in suscripciones}
                
                epsas = session.exec(select(EPSA).where(EPSA.id.in_(epsa_ids))).all()
                planes = session.exec(select(Plan).where(Plan.id.in_(plan_ids))).all()
                
                epsas_dict = {e.id: e for e in epsas}
                planes_dict = {p.id: p for p in planes}
                
                estado_icono = {
                    EstadoSuscripcion.TRIAL: "🟡",
                    EstadoSuscripcion.ACTIVA: "🟢",
                    EstadoSuscripcion.VENCIDA: "🔴",
                    EstadoSuscripcion.CANCELADA: "⚫"
                }
                
                data = []
                for s in suscripciones:
                    epsa = epsas_dict.get(s.epsa_id)
                    plan = planes_dict.get(s.plan_id)
                    dias_restantes = None
                    if s.fecha_fin:
                        dias_restantes = (s.fecha_fin - date.today()).days
                    
                    data.append({
                        "ID": s.id,
                        "EPSA": epsa.nombre if epsa else "N/A",
                        "Plan": plan.nombre if plan else "N/A",
                        "Estado": f"{estado_icono.get(s.estado, '⚪')} {s.estado.value.upper()}",
                        "Inicio": s.fecha_inicio.strftime("%d/%m/%Y"),
                        "Fin": s.fecha_fin.strftime("%d/%m/%Y") if s.fecha_fin else "Indefinido",
                        "Días rest.": dias_restantes if dias_restantes is not None else "-",
                        "Pago/mes": f"${s.monto_pagado_mes:,.2f}",
                        "Desc.": f"{s.descuento_porcentaje}%"
                    })
        
        if not suscripciones:
            st.info("No hay suscripciones registradas. Crea una nueva desde el panel derecho.")
        else:
            st.dataframe(data, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("➕ Nueva suscripción")
        _form_nueva_suscripcion()
        
        st.divider()
        st.subheader("⚙️ Acciones")
        _acciones_suscripcion()


def _form_nueva_suscripcion():
    with get_session() as session:
        epsas = session.exec(select(EPSA)).all()
        planes = session.exec(select(Plan)).all()
        
        suscripciones_activas = session.exec(
            select(Suscripcion).where(
                Suscripcion.estado.in_([EstadoSuscripcion.TRIAL, EstadoSuscripcion.ACTIVA])
            )
        ).all()
        epsas_con_suscripcion = {s.epsa_id for s in suscripciones_activas}
        epsas_disponibles = [e for e in epsas if e.id not in epsas_con_suscripcion]
    
    if not epsas_disponibles:
        st.warning("Todas las EPSAs tienen suscripción activa.")
        return
    
    if not planes:
        st.error("No hay planes configurados.")
        return
    
    with st.form("form_nueva_suscripcion"):
        epsa_sel = st.selectbox(
            "EPSA",
            options=[f"{e.nombre} ({e.ciudad})" for e in epsas_disponibles]
        )
        epsa_id = next(e.id for e in epsas_disponibles if f"{e.nombre} ({e.ciudad})" == epsa_sel)
        
        plan_sel = st.selectbox(
            "Plan",
            options=[f"{p.nombre} - ${p.precio_mensual_usd:,.2f}/año" for p in planes]
        )
        plan_id = next(p.id for p in planes if p.nombre in plan_sel)
        
        tipo_periodo = st.selectbox(
            "Tipo",
            ["TRIAL (30 días gratis)", "Anual", "Bianual"]
        )
        
        submitted = st.form_submit_button("Crear", type="primary", use_container_width=True)
        
        if submitted:
            plan = next(p for p in planes if p.id == plan_id)
            
            if tipo_periodo.startswith("TRIAL"):
                fecha_fin = date.today() + timedelta(days=30)
                estado = EstadoSuscripcion.TRIAL
                descuento = 100
                monto = 0.0
            elif tipo_periodo.startswith("Anual"):
                fecha_fin = date.today() + timedelta(days=365)
                estado = EstadoSuscripcion.ACTIVA
                descuento = 0
                monto = plan.precio_mensual_usd
            else:
                fecha_fin = date.today() + timedelta(days=730)
                estado = EstadoSuscripcion.ACTIVA
                descuento = 16.67
                monto = plan.precio_mensual_usd * (1 - descuento/100)
            
            try:
                with get_session() as session:
                    nueva = Suscripcion(
                        epsa_id=epsa_id,
                        plan_id=plan_id,
                        fecha_inicio=date.today(),
                        fecha_fin=fecha_fin,
                        estado=estado,
                        monto_pagado_mes=monto,
                        descuento_porcentaje=int(descuento),
                        metodo_pago="trial" if estado == EstadoSuscripcion.TRIAL else "pendiente"
                    )
                    session.add(nueva)
                    session.commit()
                st.success(f"✅ Suscripción creada para {epsa_sel}")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error: {e}")


def _acciones_suscripcion():
    sus_id = st.number_input("ID Suscripción", min_value=1, step=1, key="acc_sus_id")
    
    accion = st.selectbox(
        "Acción",
        ["Cambiar estado", "Extender período", "Aplicar descuento"],
        key="acc_sus_tipo"
    )
    
    if accion == "Cambiar estado":
        nuevo_estado = st.selectbox(
            "Nuevo estado",
            [e.value for e in EstadoSuscripcion],
            key="acc_sus_estado"
        )
        if st.button("Aplicar", key="btn_cambiar_estado", use_container_width=True):
            with get_session() as session:
                sus = session.get(Suscripcion, sus_id)
                if sus:
                    sus.estado = nuevo_estado
                    session.add(sus)
                    session.commit()
                    st.success(f"Estado cambiado a {nuevo_estado}")
                    st.rerun()
                else:
                    st.error("No encontrada")
    
    elif accion == "Extender período":
        meses = st.number_input("Años", min_value=1, max_value=12, value=1, key="acc_sus_meses")
        if st.button("Extender", key="btn_extender", use_container_width=True):
            with get_session() as session:
                sus = session.get(Suscripcion, sus_id)
                if sus:
                    if sus.fecha_fin:
                        sus.fecha_fin = sus.fecha_fin + timedelta(days=365*meses)
                    else:
                        sus.fecha_fin = date.today() + timedelta(days=365*meses)
                    session.add(sus)
                    session.commit()
                    st.success("Período extendido")
                    st.rerun()
                else:
                    st.error("No encontrada")
    
    else:  # Descuento
        desc = st.number_input("Descuento %", min_value=0, max_value=100, value=0, key="acc_sus_desc")
        if st.button("Aplicar", key="btn_descuento", use_container_width=True):
            with get_session() as session:
                sus = session.get(Suscripcion, sus_id)
                plan = session.get(Plan, sus.plan_id) if sus else None
                if sus and plan:
                    sus.descuento_porcentaje = desc
                    sus.monto_pagado_mes = plan.precio_mensual_usd * (1 - desc/100)
                    session.add(sus)
                    session.commit()
                    st.success(f"Descuento aplicado. Nuevo monto: ${sus.monto_pagado_mes:,.2f}")
                    st.rerun()
                else:
                    st.error("No encontrada")


# ============================================================
# SECCIÓN: PLANES
# ============================================================
# Temporal
def _mostrar_planes():
    with get_session() as session:
        planes = session.exec(select(Plan)).all()
    
    if not planes:
        st.warning("No hay planes configurados.")
        return
    
    st.subheader("Planes disponibles")
    
    cols = st.columns(len(planes))
    for col, plan in zip(cols, planes):
        with col:
            st.metric(plan.nombre, f"${plan.precio_mensual_usd:,.2f}/año")
            with st.expander("Detalles"):
                st.markdown(f"**Usuarios:** {'∞' if plan.max_usuarios == -1 else plan.max_usuarios}")
                st.markdown(f"**EPSAs:** {'∞' if plan.max_epsas == -1 else plan.max_epsas}")
                st.markdown(f"**Cajeros:** {'∞' if plan.max_cajeros == -1 else plan.max_cajeros}")
                st.markdown(f"**Reportes:** {'✅' if plan.tiene_reportes_avanzados else '❌'}")
                st.markdown(f"**Backup:** {'✅' if plan.tiene_backup else '❌'}")
                st.markdown(f"**API:** {'✅' if plan.tiene_api else '❌'}")
                st.markdown(f"**Soporte:** {plan.soporte_nivel}")


# ============================================================
# SECCIÓN: USUARIOS DEL SISTEMA
# ============================================================

def _mostrar_usuarios_sistema():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Usuarios registrados")
        usuarios = listar_usuarios_sistema()
        
        if not usuarios:
            st.info("No hay usuarios del sistema.")
        else:
            st.dataframe(usuarios, use_container_width=True, hide_index=True)
            
            # Métricas
            cols = st.columns(2)
            with cols[0]:
                st.metric("Total", len(usuarios))
            with cols[1]:
                admins = sum(1 for u in usuarios if u["rol"] == "admin_epsa")
                st.metric("Admin EPSA", admins)
    
    with col2:
        st.subheader("➕ Nuevo usuario")
        _form_nuevo_usuario()
        
        st.divider()
        st.subheader("⚙️ Acciones")
        _acciones_usuario()


def _form_nuevo_usuario():
    with get_session() as session:
        epsas = get_all_epsas(session)
    
    if not epsas:
        st.warning("Crea una EPSA primero.")
        return
    
    with st.form("form_nuevo_usuario"):
        username = st.text_input("Usuario", placeholder="alcalde_colquiri")
        password = st.text_input("Contraseña", type="password", placeholder="Mín. 6 caracteres")
        nombre = st.text_input("Nombre completo", placeholder="Juan Pérez")
        
        rol = st.selectbox(
            "Rol",
            ["admin_epsa"],
            format_func=lambda x: {"admin_epsa": "🏛️ Admin EPSA"}.get(x, x)
        )
        
        epsa_opciones = {f"{e.nombre} ({e.ciudad})": e.id for e in epsas}
        epsa_sel = st.selectbox("EPSA asignada", list(epsa_opciones.keys()))
        epsa_id = epsa_opciones[epsa_sel]
        
        submitted = st.form_submit_button("Crear", type="primary", use_container_width=True)
        
        if submitted:
            if not username or not password or not nombre:
                st.error("Todos los campos son obligatorios.")
            elif len(password) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres.")
            else:
                ok, mensaje = crear_usuario_sistema(
                    username=username.strip(),
                    password=password,
                    role=rol,
                    epsa_id=epsa_id,
                    nombre_completo=nombre.strip()
                )
                if ok:
                    st.success(mensaje)
                    st.balloons()
                else:
                    st.error(mensaje)


def _acciones_usuario():
    usuarios = listar_usuarios_sistema()
    gestionables = [u for u in usuarios if u["rol"] != "super_admin"]
    
    if not gestionables:
        st.info("Solo existe super_admin.")
        return
    
    user_sel = st.selectbox(
        "Usuario",
        options=[f"{u['username']} ({u['nombre']})" for u in gestionables],
        key="acc_user_sel"
    )
    user_id = next(u["id"] for u in gestionables if f"{u['username']} ({u['nombre']})" == user_sel)
    
    accion = st.selectbox(
        "Acción",
        ["Activar/Desactivar", "Resetear contraseña"],
        key="acc_user_tipo"
    )
    
    if accion == "Activar/Desactivar":
        estado_actual = next(u["activo"] for u in gestionables if u["id"] == user_id)
        st.info(f"Estado actual: {estado_actual}")
        nuevo = st.toggle("Activo", value=(estado_actual == "✅"), key="acc_user_toggle")
        
        if st.button("Aplicar", key="btn_user_estado", use_container_width=True):
            ok = cambiar_estado_usuario(user_id, nuevo)
            if ok:
                st.success("Estado actualizado.")
                st.rerun()
            else:
                st.error("Error.")
    
    else:  # Reset password
        nueva = st.text_input("Nueva contraseña", type="password", key="acc_user_pass")
        if st.button("Resetear", key="btn_user_pass", use_container_width=True):
            if not nueva or len(nueva) < 6:
                st.error("Mínimo 6 caracteres.")
            else:
                ok = reset_password(user_id, nueva)
                if ok:
                    st.success("Contraseña actualizada.")
                else:
                    st.error("Error.")