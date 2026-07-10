import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()
os.makedirs("data", exist_ok=True)
os.makedirs("data/logos", exist_ok=True)
os.makedirs("recibos", exist_ok=True)

from src.database.connection import init_db, get_session
from src.database.crud import get_all_epsas, create_epsa
from src.utils.auth import login_form, logout, seed_planes, verificar_suscripcion_activa, crear_usuarios_por_defecto
from src.database.models import EPSA, Plan, UsuarioSistema
from pathlib import Path

# 2. FUNCIÓN PRINCIPAL
# ============================================================

def main():
    st.set_page_config(page_title="EPSACOMUNITARIA - Gestión de Agua Comunitaria", layout="wide")
    # Solo si no está inicializado
    if "db_initialized" not in st.session_state:
        try:
            init_db()
            seed_planes()
            crear_usuarios_por_defecto()   # Reemplaza a init_auth_db
            st.session_state["db_initialized"] = True
            st.success("✅ Base de datos inicializada correctamente")
        except Exception as e:
            st.error(f"❌ Error al inicializar la base de datos: {e}")
            st.stop()  # Detiene la ejecución si falla la inicialización
    
    #init_db()
    #seed_planes()    #PLANES DE SUSCRIPCION
    #crear_usuarios_por_defecto()
    
    # ========== BLOQUEO DE LOGIN ==========
    if "user_id" not in st.session_state:
        login_form()
        return  # Detener aquí hasta que inicie sesión
    
    # ========== DATOS DEL USUARIO LOGUEADO ==========
    user_role = st.session_state.get("user_role")
    user_name = st.session_state.get("user_name", "Usuario")
    epsa_id = st.session_state.get("epsa_id")
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"
    
    # 3. SIDEBAR (MENÚ POR ROLES)
    # ============================================================
    with st.sidebar:
        logo_path = Path("data/logos/ic_epsa.jpg")
        if logo_path.exists():
            st.image(str(logo_path), width=150)
        else:
            st.image("https://via.placeholder.com/150x80?text=EPSACOL", width=150)

        # Info del usuario
        st.markdown(f"**👤 {user_name}**")
        st.caption(f"Rol: `{user_role}`")
        st.divider()
        
        # ---------- SELECTOR DE EPSA ----------
        if user_role == "super_admin":
            with get_session() as session:
                epsas = get_all_epsas(session)
            
            epsa_options = {e.nombre: e.id for e in epsas}
            opciones = list(epsa_options.keys()) if epsas else []
            opciones.insert(0, "-- Crear nueva --")
            
            selected = st.selectbox("Seleccionar EPSA", opciones)
            
            if selected == "-- Crear nueva --":
                new_name = st.text_input("Nombre de la nueva EPSA")
                new_city = st.text_input("Ciudad")
                if st.button("Crear EPSA", width='stretch'):
                    if new_name and new_city:
                        with get_session() as sess:
                            epsa = create_epsa(sess, new_name, new_city)
                            st.session_state.epsa_id = epsa.id
                            st.rerun()
                    else:
                        st.error("Complete nombre y ciudad")
            else:
                st.session_state.epsa_id = epsa_options[selected]
                st.success(f"Activa: {selected}")
        
        #hassta aqui...
        elif user_role in ("admin_epsa"):
            st.header("Mi EPSA")
            
            if not epsa_id:
                st.warning("⚠️ No tienes una EPSA asignada. Contacta al administrador.")
                
                # Opcional: permitir seleccionar de las existentes (solo para admin_epsa)
                if user_role == "admin_epsa":
                    with get_session() as session:
                        epsas = get_all_epsas(session)
                        if epsas:
                            seleccion = st.selectbox("Selecciona tu EPSA", [e.nombre for e in epsas])
                            if st.button("Confirmar", width='stretch', key="btn_confirmar_epsa"):
                                selected = [e for e in epsas if e.nombre == seleccion][0]
                                st.session_state.epsa_id = selected.id
                                st.rerun()            
            else:
                # ✅ SÍ tiene EPSA asignada - mostrar info y estado de suscripción
                with get_session() as session:
                    epsa = session.get(EPSA, epsa_id)
                    if epsa:
                        st.info(f"**{epsa.nombre}**\n📍 {epsa.ciudad}")
                ok, mensaje = verificar_suscripcion_activa(epsa_id)                
                if ok:
                    if "🟡" in mensaje:  # Trial
                        st.warning(mensaje)
                    else:
                        st.success(mensaje)
                else:
                    st.error(mensaje)

        # ---------- MENÚ DE NAVEGACIÓN ----------
        st.divider()
        st.subheader("Menú")
        
        if st.button("📊 Presentacion", width='stretch'):
            st.session_state.current_page = "dashboard"
            st.rerun()        
        if user_role in ("super_admin", "admin_epsa"):
            if st.button("⚙️ Configuración EPSA", width='stretch'):
                st.session_state.current_page = "configuracion_epsa"
                st.rerun()        
        if user_role in ("super_admin", "admin_epsa"):
            if st.button("👥 Gestión de Usuarios", width='stretch'):
                st.session_state.current_page = "gestion_usuarios"
                st.rerun()        
        #if user_role in ("super_admin", "admin_epsa"):
        if st.button("💰 Tarifas", width='stretch'):
            st.session_state.current_page = "configuracion_tarifas"
            st.rerun()        
        if user_role in ("super_admin", "admin_epsa"):
            if st.button("📝 Toma de Lecturas", width='stretch'):
                st.session_state.current_page = "toma_lecturas"
                st.rerun()        
        if st.button("💵 Caja / Pagos", width='stretch'):
            st.session_state.current_page = "caja_pagos"
            st.rerun()        
        if user_role in ("super_admin", "admin_epsa"):
            if st.button("🔄 Cierre de Periodo", width='stretch'):
                st.session_state.current_page = "cierre_periodo"
                st.rerun()
            if st.button("📄 Reportes", width='stretch'):
                st.session_state.current_page = "reportes"
                st.rerun()              
        # Solo super_admin ve esto
        if user_role == "super_admin":
            st.divider()
            if st.button("🛠️ Administración", width='stretch', key="btn_admin"):
                st.session_state.current_page = "administracion"
                st.rerun()
        # Logout
        st.divider()
        if st.button("🚪 Cerrar Sesión", width='stretch'):
            logout()

    # 4. CARGAR PÁGINA SELECCIONADA
    # ============================================================
    try:
        page = st.session_state.current_page
        
        if page == "dashboard":
            from src.ui.pages import dashboard
            dashboard.show()
        elif page == "configuracion_epsa":
            from src.ui.pages import configuracion_epsa
            configuracion_epsa.show()
        elif page == "gestion_usuarios":
            from src.ui.pages import gestion_usuarios
            gestion_usuarios.show()
        elif page == "configuracion_tarifas":
            from src.ui.pages import configuracion_tarifas
            configuracion_tarifas.show()
        elif page == "toma_lecturas":
            from src.ui.pages import toma_lecturas
            toma_lecturas.show()
        elif page == "caja_pagos":
            from src.ui.pages import caja_pagos
            caja_pagos.show()
        elif page == "cierre_periodo":
            from src.ui.pages import cierre_periodo
            cierre_periodo.show()
        elif page == "reportes":
            from src.ui.pages import reportes
            reportes.show()
        elif page == "administracion":
            from src.ui.pages import administracion
            administracion.show()
        else:
            from src.ui.pages import dashboard
            dashboard.show()
            
    except ImportError as e:
        import traceback
        st.error(f"Error al cargar página: {e}")
        st.code(traceback.format_exc())
    except Exception as e:
        st.error(f"Error inesperado: {e}")

if __name__ == "__main__":
    main()