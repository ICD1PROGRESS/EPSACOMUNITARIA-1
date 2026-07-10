# src/ui/pages/configuracion_epsa.py
import streamlit as st
from pathlib import Path
from datetime import date
from sqlmodel import select
from src.database.connection import get_session
from src.database.models import EPSA, ConfiguracionEPSA, Periodo
from src.database.crud import create_epsa, get_all_epsas
from src.utils.recibo_pdf import generar_recibo_pdf


# ============================================================
# FUNCIÓN AUXILIAR: FORMULARIO DE CONFIGURACIÓN
# ============================================================
def _render_formulario_config(epsa_id: int, epsa_nombre: str):
    """
    Renderiza el formulario de configuración de una EPSA.
    Usado por admin_epsa (su propia EPSA) y super_admin (EPSA activa).
    """
    # Cargar datos DENTRO de sesión, extraer valores primitivos
    with get_session() as session:
        config = session.exec(
            select(ConfiguracionEPSA).where(ConfiguracionEPSA.epsa_id == epsa_id)
        ).first()

        if not config:
            config = ConfiguracionEPSA(
                epsa_id=epsa_id,
                membrete_texto=epsa_nombre
            )
            session.add(config)
            session.commit()
            session.refresh(config)

        # Extraer valores primitivos ANTES de cerrar la sesión
        config_membrete = config.membrete_texto or epsa_nombre
        config_direccion = config.direccion or ""
        config_telefono = config.telefono or ""
        config_email = config.email or ""
        config_sitio_web = config.sitio_web or ""
        config_logo_path = config.logo_path

    st.subheader(f"Configuración: {epsa_nombre}")

    # Directorio para logos
    logos_dir = Path("data/logos")
    logos_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # FORMULARIO DE CONFIGURACIÓN
    # ------------------------------------------------------------------
    with st.form("form_config_epsa"):
        st.markdown("### 📝 Datos del Membrete")

        membrete = st.text_input(
            "Texto del membrete *",
            value=config_membrete,
            placeholder="Ej: EPSA MUNICIPAL DE COLQUIRI"
        )

        direccion = st.text_input(
            "Dirección",
            value=config_direccion,
            placeholder="Ej: Plaza Principal s/n, Colquiri"
        )

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            telefono = st.text_input(
                "Teléfono",
                value=config_telefono,
                placeholder="Ej: 2-1234567"
            )
        with col_t2:
            email = st.text_input(
                "Email",
                value=config_email,
                placeholder="Ej: epsa@colquiri.gob.bo"
            )

        sitio_web = st.text_input(
            "Sitio web",
            value=config_sitio_web,
            placeholder="Ej: https://www.colquiri.gob.bo"
        )

        st.markdown("### 🖼️ Logo de la EPSA")

        # Mostrar logo actual si existe
        if config_logo_path:
            logo_path = Path(config_logo_path)
            if logo_path.exists():
                st.image(str(logo_path), width=150, caption="Logo actual")
            else:
                st.warning("⚠️ La ruta del logo existe en la BD pero el archivo no se encuentra.")
        else:
            st.info("No hay logo configurado. Suba uno a continuación.")

        logo_file = st.file_uploader(
            "Subir nuevo logo (PNG, JPG, JPEG)",
            type=["png", "jpg", "jpeg"],
            help="Tamaño recomendado: 150x150 píxeles. Se redimensionará automáticamente."
        )

        # Checkbox para eliminar logo
        eliminar_logo = False
        if config_logo_path:
            eliminar_logo = st.checkbox("🗑️ Eliminar logo actual", value=False)

        st.markdown("---")
        submitted = st.form_submit_button("💾 Guardar Configuración", type="primary", width='stretch')

        if submitted:
            try:
                with get_session() as session:
                    config_db = session.exec(
                        select(ConfiguracionEPSA).where(ConfiguracionEPSA.epsa_id == epsa_id)
                    ).first()

                    # Actualizar campos de texto
                    config_db.membrete_texto = membrete.strip()
                    config_db.direccion = direccion.strip() if direccion else None
                    config_db.telefono = telefono.strip() if telefono else None
                    config_db.email = email.strip() if email else None
                    config_db.sitio_web = sitio_web.strip() if sitio_web else None

                    # Manejar logo
                    if eliminar_logo and config_db.logo_path:
                        old_path = Path(config_db.logo_path)
                        if old_path.exists():
                            old_path.unlink()
                        config_db.logo_path = None

                    elif logo_file is not None:
                        # Guardar nuevo logo
                        extension = logo_file.name.split('.')[-1].lower()
                        nombre_archivo = f"epsa_{epsa_id}_{date.today().strftime('%Y%m%d')}.{extension}"
                        ruta_logo = logos_dir / nombre_archivo

                        # Eliminar logo anterior si existe
                        if config_db.logo_path:
                            old_path = Path(config_db.logo_path)
                            if old_path.exists():
                                old_path.unlink()

                        # Guardar archivo
                        with open(ruta_logo, "wb") as f:
                            f.write(logo_file.getbuffer())

                        config_db.logo_path = str(ruta_logo)

                    session.add(config_db)
                    session.commit()

                st.success("✅ Configuración guardada exitosamente.")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al guardar configuración: {e}")

    # ------------------------------------------------------------------
    # PREVISUALIZACIÓN DE RECIBO
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("👁️ Previsualización de Recibo")
    st.markdown("Vista previa de cómo se verá el recibo con la configuración actual.")

    if st.button("🖨️ Generar recibo de prueba", type="secondary"):
        try:
            # Recargar config fresca para el recibo
            with get_session() as session:
                config_fresh = session.exec(
                    select(ConfiguracionEPSA).where(ConfiguracionEPSA.epsa_id == epsa_id)
                ).first()

            # Crear datos de prueba
            datos_prueba = {
                'codigo': 'DEMO-001',
                'nombre': 'USUARIO DE PRUEBA',
                'ci': '1234567',
                'zona': 'ZONA CENTRAL',
                'medidor': 'A12L000001',
                'periodo': 'DEMO - 2024',
                'lectura_anterior': 10.00,
                'lectura_actual': 15.50,
                'consumo': 5.50,
                'importe_consumo': 45.50,
                'reconexion': 20.00,
                'deuda': 30.00,
                'total': 95.50,
                'nro_recibo': 'REC-DEMO-001',
                'fecha': date.today(),
                'efectivo': 100.00,
                'cambio': 4.50,
                'es_deuda_especifica': False
            }

            # Usuario ficticio para el recibo
            class UsuarioDemo:
                def __init__(self):
                    self.codigo = 'DEMO-001'
                    self.nombre = 'USUARIO DE PRUEBA'
                    self.ci = '1234567'
                    self.zona = 'ZONA CENTRAL'
                    self.nro_medidor = 'A12L000001'

            usuario_demo = UsuarioDemo()

            ruta_pdf = generar_recibo_pdf(usuario_demo, datos_prueba, config_fresh)

            st.success("✅ Recibo de prueba generado.")
            with open(ruta_pdf, "rb") as f:
                st.download_button(
                    "📄 Descargar recibo de prueba",
                    data=f,
                    file_name=f"recibo_prueba_{epsa_nombre.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"❌ Error al generar recibo de prueba: {e}")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================
def show():
    # ========== CONTROL DE ACCESO ==========
    user_role = st.session_state.get("user_role")

    if user_role not in ("super_admin", "admin_epsa"):
        st.error("🚫 No tienes permiso para acceder a esta sección.")
        st.stop()

    epsa_id_session = st.session_state.get("epsa_id")

    # ==================================================================
    # ADMIN EPSA: SOLO VE SU PROPIA EPSA
    # ==================================================================
    if user_role == "admin_epsa":
        if not epsa_id_session:
            st.error("⚠️ No tienes una EPSA asignada.")
            return

        # Forzar que solo vea su EPSA
        st.title("⚙️ Mi Configuración de EPSA")
        st.caption(f"Administrando: EPSA #{epsa_id_session}")

        # Cargar nombre de la EPSA para el título
        with get_session() as session:
            epsa = session.get(EPSA, epsa_id_session)
            if not epsa:
                st.error("EPSA no encontrada.")
                return
            epsa_nombre = epsa.nombre

        # Renderizar formulario (compartido con super_admin)
        _render_formulario_config(epsa_id_session, epsa_nombre)
        return  # ← IMPORTANTE: evita que caiga en el código de super_admin

    # ==================================================================
    # SUPER ADMIN: VE TODAS LAS EPSAs
    # ==================================================================
    st.title("⚙️ Configuración de EPSA")
    st.caption("Sistema de Gestión Integral de Agua Potable Comunitaria")

    epsa_id = st.session_state.get("epsa_id")
    tab_lista, tab_nueva, tab_config = st.tabs([
        "📋 EPSAs Registradas",
        "➕ Nueva EPSA",
        "🔧 Configurar EPSA Activa"
    ])

    # ==================================================================
    # TAB 1: LISTA DE EPSAs
    # ==================================================================
    with tab_lista:
        with get_session() as session:
            epsas = get_all_epsas(session)

        if not epsas:
            st.info("No hay EPSAs registradas. Crea una en la pestaña 'Nueva EPSA'.")
        else:
            st.subheader("Listado de EPSAs")
            
            # PRECARGA: evita N+1. Una sola sesión para todas las configs y periodos activos
            epsa_ids = [e.id for e in epsas]
            with get_session() as session:
                configs = session.exec(
                    select(ConfiguracionEPSA).where(ConfiguracionEPSA.epsa_id.in_(epsa_ids))
                ).all()
                periodos = session.exec(
                    select(Periodo).where(Periodo.epsa_id.in_(epsa_ids), Periodo.activo == True)
                ).all()
            
            configs_dict = {c.epsa_id: c for c in configs}
            periodos_dict = {p.epsa_id: p for p in periodos}
            
            data = []
            for e in epsas:
                config = configs_dict.get(e.id)
                periodo = periodos_dict.get(e.id)
                
                data.append({
                    "ID": e.id,
                    "Nombre": e.nombre,
                    "Ciudad": e.ciudad,
                    "Membrete": config.membrete_texto if config else "Sin configurar",
                    "Logo": "✅ Sí" if (config and config.logo_path) else "❌ No",
                    "Periodo activo": periodo.nombre if periodo else "Sin periodo",
                    "Creada": e.created_at.strftime("%d/%m/%Y") if e.created_at else "-"
                })

            st.dataframe(data, use_container_width=True, hide_index=True)

            # Seleccionar EPSA activa
            st.divider()
            st.subheader("Seleccionar EPSA activa")
            opciones = {f"{e.nombre} ({e.ciudad})": e.id for e in epsas}
            seleccion = st.selectbox("EPSA", list(opciones.keys()), key="cfg_sel_epsa")

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("✅ Activar selección", type="primary"):
                    st.session_state.epsa_id = opciones[seleccion]
                    st.success("EPSA activa actualizada.")
                    st.rerun()
            with col2:
                if st.session_state.get("epsa_id"):
                    epsa_activa_nombre = next(
                        (e.nombre for e in epsas if e.id == st.session_state.epsa_id),
                        "Desconocida"
                    )
                    st.info(f"Actualmente activa: **{epsa_activa_nombre}**")

    # ==================================================================
    # TAB 2: NUEVA EPSA
    # ==================================================================
    with tab_nueva:
        st.subheader("Crear nueva EPSA")
        st.markdown("""
        Complete los datos de la nueva EPSA. Después de crearla, podrá configurar 
        el logo, membrete y otros datos en la pestaña 'Configurar EPSA Activa'.
        """)

        with st.form("form_nueva_epsa"):
            nombre = st.text_input("Nombre de la EPSA *", placeholder="Ej: EPSA Municipal de Colquiri")
            ciudad = st.text_input("Ciudad *", placeholder="Ej: Colquiri")

            st.markdown("**Período inicial** (opcional)")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                nombre_periodo = st.text_input(
                    "Nombre del primer período",
                    value=f"{date.today().strftime('%B').upper()} - {date.today().year}",
                    placeholder="Ej: ENERO - 2024"
                )
            with col_p2:
                fecha_inicio = st.date_input("Fecha de inicio", value=date.today())

            submitted = st.form_submit_button("➕ Crear EPSA", type="primary", width='stretch')

            if submitted:
                if not nombre or not ciudad:
                    st.error("Nombre y ciudad son obligatorios.")
                else:
                    try:
                        with get_session() as session:
                            # Verificar que no exista
                            existente = session.exec(
                                select(EPSA).where(EPSA.nombre == nombre.strip())
                            ).first()
                            if existente:
                                st.error(f"Ya existe una EPSA con el nombre '{nombre}'.")
                                st.stop()

                            # Crear EPSA
                            nueva_epsa = create_epsa(session, nombre.strip(), ciudad.strip())
                            nueva_epsa_id = nueva_epsa.id
                            nueva_epsa_nombre = nueva_epsa.nombre

                            # Crear configuración vacía
                            config = ConfiguracionEPSA(
                                epsa_id=nueva_epsa_id,
                                membrete_texto=nueva_epsa_nombre
                            )
                            session.add(config)

                            # Crear periodo inicial
                            if nombre_periodo:
                                periodo = Periodo(
                                    epsa_id=nueva_epsa_id,
                                    nombre=nombre_periodo.upper(),
                                    fecha_inicio=fecha_inicio,
                                    fecha_fin=fecha_inicio,
                                    activo=True,
                                    cerrado=False
                                )
                                session.add(periodo)

                            session.commit()

                        # Activar automáticamente
                        st.session_state.epsa_id = nueva_epsa_id

                        st.success(f"✅ EPSA '{nueva_epsa_nombre}' creada y activada exitosamente.")
                        st.info(f"Periodo inicial: **{nombre_periodo}**")
                        st.balloons()

                    except Exception as e:
                        st.error(f"❌ Error al crear EPSA: {e}")

    # ==================================================================
    # TAB 3: CONFIGURAR EPSA ACTIVA
    # ==================================================================
    with tab_config:
        if not epsa_id:
            st.warning("⚠️ Primero selecciona o crea una EPSA.")
            return

        # Cargar nombre de la EPSA
        with get_session() as session:
            epsa = session.get(EPSA, epsa_id)
            if not epsa:
                st.error("EPSA no encontrada.")
                return
            epsa_nombre = epsa.nombre

        # Renderizar formulario compartido
        _render_formulario_config(epsa_id, epsa_nombre)