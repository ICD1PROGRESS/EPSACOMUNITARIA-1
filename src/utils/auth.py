# src/utils/auth.py
import streamlit as st
import hashlib
import secrets
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Session, select
from typing import Optional

# Importamos el engine ya creado
from src.database.connection import engine
from src.database.models import UsuarioSistema, EstadoSuscripcion, Suscripcion, EPSA, Plan

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashea una contraseña con SHA256 + salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    pwdhash = hashlib.sha256((password + salt).encode()).hexdigest()
    return pwdhash, salt


def verificar_password(password: str, salt: str, password_hash: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    pwdhash, _ = hash_password(password, salt)
    return pwdhash == password_hash

# ============================================
# VERIFICACIÓN DE SUSCRIPCIÓN
# ============================================

def verificar_suscripcion_activa(epsa_id: int) -> tuple[bool, str]:
    """
    Verifica si la EPSA tiene una suscripción activa o en trial.
    Retorna (True, mensaje) si está OK, (False, mensaje_error) si no.
    """
    with Session(engine) as session:
        suscripcion = session.exec(
            select(Suscripcion).where(
                Suscripcion.epsa_id == epsa_id,
                Suscripcion.estado.in_([EstadoSuscripcion.TRIAL, EstadoSuscripcion.ACTIVA])
            )
        ).first()
        
        if not suscripcion:
            return False, "⚠️ Esta EPSA no tiene una suscripción activa. Contacta al administrador."
        
        if suscripcion.fecha_fin and suscripcion.fecha_fin < date.today():
            dias_vencido = (date.today() - suscripcion.fecha_fin).days
            return False, f"⚠️ Tu suscripción venció hace {dias_vencido} días. Renueva para continuar."
        
        # Todo OK
        dias_restantes = None
        if suscripcion.fecha_fin:
            dias_restantes = (suscripcion.fecha_fin - date.today()).days
        
        if suscripcion.estado == EstadoSuscripcion.TRIAL:
            return True, f"🟡 Estás en período de prueba. Días restantes: {dias_restantes or 'N/A'}"
        
        return True, f"🟢 Suscripción activa. Días restantes: {dias_restantes or 'N/A'}"

def crear_usuarios_por_defecto():
    """Inserta los usuarios admin y epsa por defecto si no existen."""
    with Session(engine) as session:
        admin = session.exec(select(UsuarioSistema).where(UsuarioSistema.username == "admin")).first()
        if not admin:
            usuarios_default = [
                ("admin", "admin123", "super_admin", None, "Administrador General"),
                ("epsa", "epsa123", "admin_epsa", None, "Jefe de EPSA"),
            ]
            for u, p, r, e, n in usuarios_default:
                h, s = hash_password(p)
                session.add(UsuarioSistema(
                    username=u,
                    password_hash=h,
                    salt=s,
                    role=r,
                    epsa_id=e,
                    nombre_completo=n,
                    activo=True
                ))
            session.commit()
            print("✅ Usuarios por defecto creados.")
        else:
            print("ℹ️ Usuarios por defecto ya existen.")
# ============================================
# INICIALIZACIÓN
# ============================================
#def init_auth_db():
#    SQLModel.metadata.create_all(engine, tables=[UsuarioSistema.__table__], checkfirst=True)
    
def seed_planes():
    """Crea los planes de suscripción si no existen."""    
    with Session(engine) as session:
        existe = session.exec(select(Plan)).first()
        if existe:
            return   
        #if session.exec(select(Plan)).first():   #Temporal - en vez de arriba
        #    return          
                
        planes = [
            Plan(
                nombre="BÁSICO",
                precio_mensual_usd=890,
                max_usuarios=500,
                max_epsas=1,
                max_cajeros=1,
                tiene_reportes_avanzados=True,
                tiene_backup=False,
                tiene_api=False,
                soporte_nivel="email"
            ),
            Plan(
                nombre="PROFESIONAL",
                precio_mensual_usd=1760,
                max_usuarios=2000,
                max_epsas=2,
                max_cajeros=3,
                tiene_reportes_avanzados=True,
                tiene_backup=True,
                tiene_api=False,
                soporte_nivel="prioritario"
            ),
            Plan(
                nombre="GOBIERNO",
                precio_mensual_usd=3490,
                max_usuarios=-1,
                max_epsas=-1,
                max_cajeros=-1,
                tiene_reportes_avanzados=True,
                tiene_backup=True,
                tiene_api=True,
                soporte_nivel="telefonico24_7"
            ),
        ]
        for p in planes:
            session.add(p)
        session.commit()
        print("✅ Planes de suscripción creados.")

# ============================================
# LOGIN / LOGOUT
# ============================================

def login_form():
    """Muestra el formulario de login. Retorna True si el login es exitoso."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 EPSACOMUNITARIA Digital")
        st.markdown("Sistema de Gestión de Agua Potable Municipal")
        st.divider()
        
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="Ej: admin")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.warning("Complete usuario y contraseña.")
                    return False
                
                with Session(engine) as session:
                    user = session.exec(
                        select(UsuarioSistema).where(
                            UsuarioSistema.username == username.strip(),
                            UsuarioSistema.activo == True
                        )
                    ).first()
                    
                    if not user:
                        st.error("Usuario no encontrado o inactivo.")
                        return False
                    
                    if not verificar_password(password, user.salt, user.password_hash):
                        st.error("Contraseña incorrecta.")
                        return False
                    
                    # Verificar suscripción para admin_epsa
                    #if user.role in ("admin_epsa") and user.epsa_id:
                    if user.role == "admin_epsa" and user.epsa_id:
                        ok, mensaje = verificar_suscripcion_activa(user.epsa_id)
                        if not ok:
                            st.error(mensaje)
                            return False
                        if "🟡" in mensaje:
                            st.warning(mensaje)
                    
                    # ÉXITO: Guardar en session_state
                    st.session_state["user_id"] = user.id
                    st.session_state["user_role"] = user.role
                    st.session_state["user_name"] = user.nombre_completo
                    st.session_state["username"] = user.username
                    
                    # Asignar EPSA según rol
                    if user.role == "super_admin":
                        st.session_state["epsa_id"] = None
                    else:
                        st.session_state["epsa_id"] = user.epsa_id
                    
                    st.session_state["current_page"] = "dashboard"
                    st.success(f"¡Bienvenido, {user.nombre_completo}!")
                    st.rerun()
                    #return True    
    return False

def logout():
    """Limpia toda la sesión y vuelve al login."""
    keys = [k for k in st.session_state.keys()]
    for k in keys:
        del st.session_state[k]
    st.rerun()

# ============================================
# CONTROL DE PERMISOS
# ============================================

def requerir_rol(roles_permitidos: list[str]):
    """Verifica que el usuario tenga un rol permitido. Si no, detiene la página."""
    rol_actual = st.session_state.get("user_role")
    if rol_actual not in roles_permitidos:
        st.error("🚫 No tienes permiso para acceder a esta sección.")
        st.stop()


def tiene_rol(roles: list[str]) -> bool:
    """Retorna True si el usuario tiene alguno de los roles indicados."""
    return st.session_state.get("user_role") in roles

# ============================================
# GESTIÓN DE USUARIOS DEL SISTEMA (para admin)
# ============================================

def crear_usuario_sistema(username: str, password: str, role: str, 
                          epsa_id: Optional[int], nombre_completo: str) -> tuple[bool, str]:

    with Session(engine) as session:
        # Verificar que no exista
        existente = session.exec(
            select(UsuarioSistema).where(UsuarioSistema.username == username)
        ).first()
        if existente:
            return False, f"El usuario '{username}' ya existe."
        
        # Verificar que la EPSA tenga suscripción si es admin_epsa o cajero
        if role in ("admin_epsa", "cajero") and epsa_id:            
            suscripcion = session.exec(
                select(Suscripcion).where(Suscripcion.epsa_id == epsa_id)
            ).first()
            if not suscripcion:
                return False, "La EPSA seleccionada no tiene una suscripción activa."
        
        # Crear usuario
        h, s = hash_password(password)
        nuevo = UsuarioSistema(
            username=username,
            password_hash=h,
            salt=s,
            role=role,
            epsa_id=epsa_id,
            nombre_completo=nombre_completo,
            activo=True
        )
        session.add(nuevo)
        session.commit()
        return True, f"Usuario '{username}' creado exitosamente."

def listar_usuarios_sistema() -> list[dict]:
    """Retorna lista de todos los usuarios del sistema."""
    with Session(engine) as session:
        usuarios = session.exec(select(UsuarioSistema)).all()
        resultado = []
        for u in usuarios:
            epsa_nombre = None
            if u.epsa_id:               
                epsa = session.get(EPSA, u.epsa_id)
                epsa_nombre = epsa.nombre if epsa else "N/A"
            
            resultado.append({
                "id": u.id,
                "username": u.username,
                "nombre": u.nombre_completo,
                "rol": u.role,
                "epsa": epsa_nombre or "Todas (super_admin)",
                "activo": "✅" if u.activo else "❌"
            })
        return resultado

def cambiar_estado_usuario(user_id: int, activo: bool) -> bool:
    """Activa o desactiva un usuario."""
    with Session(engine) as session:
        user = session.get(UsuarioSistema, user_id)
        if not user:
            return False
        user.activo = activo
        session.add(user)
        session.commit()
        return True

def reset_password(user_id: int, nueva_password: str) -> bool:
    """Resetea la contraseña de un usuario."""
    with Session(engine) as session:
        user = session.get(UsuarioSistema, user_id)
        if not user:
            return False
        h, s = hash_password(nueva_password)
        user.password_hash = h
        user.salt = s
        session.add(user)
        session.commit()
        return True