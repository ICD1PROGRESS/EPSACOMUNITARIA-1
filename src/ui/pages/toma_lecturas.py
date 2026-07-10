import streamlit as st
import pandas as pd
from datetime import date
from sqlmodel import Session, select
from src.database.connection import get_session
from src.database.models import Usuario, Lectura
from src.database.crud import (
    get_usuarios_by_epsa, 
    get_usuario_by_codigo, 
    get_tarifas_by_epsa,
    get_periodo_activo_nombre,
    get_ultima_lectura
)
from src.business.tarifa_service import calcular_importe_consumo


def show():
    st.title("📝 Toma de Lecturas")
    
    # Leer epsa_id directamente de session_state
    epsa_id = st.session_state.get("epsa_id")
    
    if not epsa_id:
        st.warning("⚠️ Primero selecciona o crea una EPSA en '⚙️ Configuración de EPSA'.")
        return

    # Obtener periodo activo
    with get_session() as session:
        periodo_activo = get_periodo_activo_nombre(session, epsa_id)

    st.success(f"📅 Período activo: **{periodo_activo}**")

    tab_manual, tab_masiva = st.tabs(["📋 Lectura Manual", "📂 Carga Masiva desde Excel"])

    # ---------- Pestaña Manual ----------
    with tab_manual:
        st.subheader("Registrar lectura individual")

        with get_session() as session:
            usuarios = get_usuarios_by_epsa(session, epsa_id)

        if not usuarios:
            st.info("No hay usuarios registrados. Ve a '👥 Gestión de Usuarios' para agregar.")
            return

        # Búsqueda flexible
        search_term = st.text_input("Buscar por código o nombre", placeholder="Ej: AP-000001 o VICTORIANO")
        filtered_users = []
        for u in usuarios:
            if search_term.lower() in u.codigo.lower() or search_term.lower() in u.nombre.lower():
                filtered_users.append(u)

        if not filtered_users:
            st.warning("No se encontraron usuarios con ese criterio.")
            return

        # Selección de usuario
        user_options = {f"{u.codigo} - {u.nombre}": u for u in filtered_users}
        selected_label = st.selectbox("Selecciona un usuario", list(user_options.keys()))
        usuario = user_options[selected_label]

        # Datos del usuario
        with st.expander("📄 Datos del usuario"):
            st.write(f"**Código:** {usuario.codigo}")
            st.write(f"**Nombre:** {usuario.nombre}")
            st.write(f"**CI:** {usuario.ci}")
            st.write(f"**Zona:** {usuario.zona}")
            st.write(f"**Medidor:** {usuario.nro_medidor}")
            st.write(f"**Categoría:** {usuario.categoria}")
            st.write(f"**Saldo actual:** {usuario.saldo_actual:.2f} Bs")

        with get_session() as session:
            # Última lectura del usuario (cualquier periodo) → será la "anterior"
            last_lect = get_ultima_lectura(session, usuario.id)
            lectura_anterior = last_lect.lectura_actual if last_lect else 0.0
            
            st.info(f"📊 Última lectura registrada: **{lectura_anterior:.2f} m³** "
                    f"(periodo: {last_lect.periodo if last_lect else 'N/A'})")

            # Verificar si ya existe lectura en el periodo activo
            lectura_existente = session.exec(
                select(Lectura).where(
                    Lectura.usuario_id == usuario.id,
                    Lectura.periodo == periodo_activo
                )
            ).first()

            if lectura_existente:
                st.warning(f"⚠️ Ya existe una lectura para {usuario.nombre} en el periodo {periodo_activo}.")
                st.write(f"**Lectura actual registrada:** {lectura_existente.lectura_actual:.2f} m³")
                return

            # Formulario de nueva lectura
            lectura_actual = st.number_input(
                "Lectura actual (m³)",
                min_value=lectura_anterior,
                step=0.01,
                format="%.2f"
            )
            fecha_toma = st.date_input("Fecha de toma", value=date.today())

            if st.button("📝 Guardar lectura", type="primary"):
                consumo = round(lectura_actual - lectura_anterior, 2)
                tarifas = get_tarifas_by_epsa(session, epsa_id)
                if tarifas:
                    importe = calcular_importe_consumo(consumo, tarifas)
                else:
                    importe = 0.0
                    st.warning("⚠️ No hay tarifas configuradas. El importe será 0. Ve a '💰 Tarifas'.")

                nueva_lectura = Lectura(
                    epsa_id=epsa_id,
                    usuario_id=usuario.id,
                    periodo=periodo_activo,
                    lectura_anterior=lectura_anterior,
                    lectura_actual=lectura_actual,
                    consumo_m3=consumo,
                    fecha_toma=fecha_toma,
                    importe_calculado=importe
                )
                session.add(nueva_lectura)
                session.commit()
                st.success(f"✅ Lectura guardada. Consumo: {consumo} m³, Importe: {importe:.2f} Bs")
                st.rerun()

    # ---------- Pestaña Carga Masiva ----------
    with tab_masiva:
        st.subheader("Cargar múltiples lecturas desde archivo Excel")
        st.markdown("""
        **Formato del archivo Excel requerido:**
        - `codigo` : código del usuario
        - `lectura_actual` : valor numérico
        - `periodo` : texto (opcional, si falta se usa el periodo activo)
        - `fecha_toma` : fecha (opcional, por defecto hoy)
        """)
        uploaded_file = st.file_uploader("Subir archivo Excel", type=["xlsx", "xls"])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file, dtype={'codigo': str})
                st.write("Vista previa:")
                st.dataframe(df.head(10))

                resumen = []
                with get_session() as session:
                    for idx, row in df.iterrows():
                        codigo = str(row['codigo']).strip()
                        lectura_actual = float(row['lectura_actual'])

                        # Periodo
                        periodo_raw = row.get('periodo')
                        if pd.isna(periodo_raw) or str(periodo_raw).strip() == '':
                            periodo = periodo_activo
                        else:
                            periodo = str(periodo_raw).strip()

                        # Fecha
                        fecha_raw = row.get('fecha_toma')
                        if pd.isna(fecha_raw):
                            fecha_toma = date.today()
                        else:
                            fecha_toma = pd.to_datetime(fecha_raw).date()

                        usuario = get_usuario_by_codigo(session, epsa_id, codigo)
                        if not usuario:
                            resumen.append({"Código": codigo, "Estado": "❌ Error", "Detalle": "Usuario no encontrado"})
                            continue

                        # Última lectura del usuario
                        last_lect = get_ultima_lectura(session, usuario.id)
                        lectura_anterior = last_lect.lectura_actual if last_lect else 0.0

                        if lectura_actual < lectura_anterior:
                            resumen.append({"Código": codigo, "Estado": "❌ Error", 
                                          "Detalle": f"Lectura actual ({lectura_actual}) < anterior ({lectura_anterior})"})
                            continue

                        consumo = round(lectura_actual - lectura_anterior, 2)
                        tarifas = get_tarifas_by_epsa(session, epsa_id)
                        if tarifas:
                            importe = calcular_importe_consumo(consumo, tarifas)
                        else:
                            importe = 0.0
                            resumen.append({"Código": codigo, "Estado": "⚠️ Advertencia", 
                                          "Detalle": "No hay tarifas configuradas"})

                        # Verificar duplicado
                        existente = session.exec(
                            select(Lectura).where(Lectura.usuario_id == usuario.id, Lectura.periodo == periodo)
                        ).first()
                        if existente:
                            resumen.append({"Código": codigo, "Estado": "⚠️ Omitido", 
                                          "Detalle": f"Ya existe lectura para período {periodo}"})
                            continue

                        nueva_lectura = Lectura(
                            epsa_id=epsa_id,
                            usuario_id=usuario.id,
                            periodo=periodo,
                            lectura_anterior=lectura_anterior,
                            lectura_actual=lectura_actual,
                            consumo_m3=consumo,
                            fecha_toma=fecha_toma,
                            importe_calculado=importe
                        )
                        session.add(nueva_lectura)
                        resumen.append({
                            "Código": codigo,
                            "Estado": "✅ OK",
                            "Detalle": f"Consumo {consumo} m³, Importe {importe:.2f} Bs"
                        })
                    session.commit()

                st.subheader("Resultado de la carga masiva")
                st.dataframe(pd.DataFrame(resumen), use_container_width=True)
                st.success("Proceso completado.")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")