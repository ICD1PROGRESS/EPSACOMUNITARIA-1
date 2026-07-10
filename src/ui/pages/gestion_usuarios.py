import streamlit as st
from sqlmodel import Session, select
from src.database.connection import get_session
from src.database.models import Usuario, Lectura, Pago, Deuda
from src.business.limites import verificar_limite_usuarios, LimiteExcedidoError
from src.database.crud import (
    get_usuarios_by_epsa, 
    create_usuario, 
    delete_usuario,
    get_ultima_lectura,
    get_ultima_lectura_periodo_cerrado, 
    importar_usuarios_desde_excel,
    get_periodo_activo_nombre
)


def show():
    st.title("👥 Gestión de Usuarios")
    
    # Leer epsa_id directamente de session_state (igual que caja_pagos.py)
    epsa_id = st.session_state.get("epsa_id")
    
    if not epsa_id:
        st.warning("⚠️ Primero selecciona o crea una EPSA en '⚙️ Configuración de EPSA'.")
        return

    tab1, tab2, tab3 = st.tabs(["📋 Listado de Usuarios", "➕ Agregar / Editar", "📂 Importar desde Excel"])

    # ---------- TAB 1: Listado tipo HOJA BASE ----------
    with tab1:
        with get_session() as session:
            usuarios = get_usuarios_by_epsa(session, epsa_id)
            periodo_actual = get_periodo_activo_nombre(session, epsa_id)

        if not usuarios:
            st.info("No hay usuarios registrados. Agrega usando las otras pestañas.")
        else:
            data = []
            for u in usuarios:
                with get_session() as session:
                    # ÚLTIMA LECTURA REGISTRADA (cualquier periodo) → "Lectura Anterior"
                    ult_lect = get_ultima_lectura_periodo_cerrado(session, u.id, periodo_actual)
                    
                    # LECTURA DEL PERIODO ACTUAL
                    lect_periodo = session.exec(
                        select(Lectura).where(
                            Lectura.usuario_id == u.id,
                            Lectura.periodo == periodo_actual
                        )
                    ).first()
                    
                    # ¿Pagó el periodo actual?
                    pago = None
                    if lect_periodo:
                        pago = session.exec(
                            select(Pago).where(
                                Pago.usuario_id == u.id,
                                Pago.periodo == periodo_actual
                            )
                        ).first()
                    
                    # Deudas pendientes
                    deudas = session.exec(
                        select(Deuda).where(
                            Deuda.usuario_id == u.id,
                            Deuda.estado == "PENDIENTE"
                        )
                    ).all()
                    total_deuda = sum(d.monto for d in deudas)
                    
                    # Cálculos
                    lect_ant = ult_lect.lectura_actual if ult_lect else 0.0
                    lect_act = lect_periodo.lectura_actual if lect_periodo else None
                    consumo = lect_periodo.consumo_m3 if lect_periodo else 0.0
                    importe = lect_periodo.importe_calculado if lect_periodo else 0.0
                    total_pagar = importe + total_deuda
                    
                    if pago:
                        estado = "PAGADO"
                    elif lect_periodo:
                        estado = "PENDIENTE"
                    else:
                        estado = "SIN LECTURA"

                data.append({
                    "Código": u.codigo,
                    "Nombre": u.nombre,
                    "Zona": u.zona,
                    "Medidor": u.nro_medidor,
                    "Lect. Ant.": f"{lect_ant:.2f}",
                    "Lect. Act.": f"{lect_act:.2f}" if lect_act is not None else "-",
                    "Consumo": f"{consumo:.2f}" if lect_periodo else "-",
                    "Importe (Bs)": f"{importe:.2f}" if lect_periodo else "-",
                    "Deuda (Bs)": f"{total_deuda:.2f}",
                    "Total (Bs)": f"{total_pagar:.2f}" if lect_periodo else f"{total_deuda:.2f}",
                    "Estado": estado,
                    "Periodo": periodo_actual,
                    "Saldo (Bs)": f"{u.saldo_actual:.2f}",
                })
            
            st.caption(f"Periodo mostrado: **{periodo_actual}** | "
                       f"**Lect. Ant.** = última lectura registrada | "
                       f"**Lect. Act.** = lectura del periodo actual")
            st.dataframe(data, use_container_width=True, hide_index=True)

            with st.expander("🗑️ Eliminar usuario"):
                with get_session() as session:
                    usuarios_list = get_usuarios_by_epsa(session, epsa_id)
                codigo_eliminar = st.selectbox("Seleccionar código a eliminar", [u.codigo for u in usuarios_list])
                if st.button("Eliminar", type="primary"):
                    usuario = next((u for u in usuarios_list if u.codigo == codigo_eliminar), None)
                    if usuario:
                        with get_session() as sess:
                            delete_usuario(sess, usuario.id)
                        st.success(f"Usuario {codigo_eliminar} eliminado.")
                        st.rerun()

    # ---------- TAB 2: Agregar/Editar ----------
    with tab2:
        st.subheader("Buscar usuario para editar o crear nuevo")
        
        codigo_buscar = st.text_input("Ingrese el código del usuario", placeholder="Ej: AP-000001")
        
        if "editando" not in st.session_state:
            st.session_state.editando = False
            st.session_state.usuario_encontrado = None
        
        col_buscar, col_limpiar = st.columns([1, 5])
        with col_buscar:
            buscar_presionado = st.button("🔍 Buscar", use_container_width=True)
        with col_limpiar:
            if st.button("🗑️ Limpiar", use_container_width=True):
                st.session_state.editando = False
                st.session_state.usuario_encontrado = None
                st.rerun()
        
        if buscar_presionado and codigo_buscar:
            with get_session() as session:
                usuario = session.exec(
                    select(Usuario).where(Usuario.epsa_id == epsa_id, Usuario.codigo == codigo_buscar)
                ).first()
            if usuario:
                st.session_state.editando = True
                st.session_state.usuario_encontrado = usuario
                st.success(f"Usuario encontrado: {usuario.nombre}")
            else:
                st.session_state.editando = False
                st.session_state.usuario_encontrado = None
                st.warning("Código no encontrado. Puedes crear un nuevo usuario con este código.")
        
        with st.form("usuario_form"):
            if st.session_state.editando and st.session_state.usuario_encontrado:
                u = st.session_state.usuario_encontrado
                codigo = st.text_input("Código del usuario *", value=u.codigo, disabled=True)
                nombre = st.text_input("Nombre completo *", value=u.nombre)
                ci = st.text_input("NIT / CI *", value=u.ci)
                zona = st.text_input("Zona", value=u.zona or "")
                nro_medidor = st.text_input("Número de medidor", value=u.nro_medidor or "")
                opciones_categoria = ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "PÚBLICO"]
                cat_actual = u.categoria.upper() if u.categoria else "RESIDENCIAL"
                if cat_actual not in opciones_categoria:
                    cat_actual = "RESIDENCIAL"
                categoria = st.selectbox("Categoría", opciones_categoria, index=opciones_categoria.index(cat_actual))
                submit_label = "✏️ Actualizar Usuario"
            else:
                codigo = st.text_input("Código del usuario *", value=codigo_buscar if codigo_buscar else "")
                nombre = st.text_input("Nombre completo *")
                ci = st.text_input("NIT / CI *")
                zona = st.text_input("Zona")
                nro_medidor = st.text_input("Número de medidor")
                categoria = st.selectbox("Categoría", ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "PÚBLICO"])
                submit_label = "➕ Guardar Nuevo Usuario"
            
            submit = st.form_submit_button(submit_label, type="primary", use_container_width=True)
            
            if submit:
                if not codigo or not nombre or not ci:
                    st.error("Código, nombre y CI son obligatorios")
                else:
                    with get_session() as sess:
                        try:
                            if st.session_state.editando and st.session_state.usuario_encontrado:
                                usuario_existente = st.session_state.usuario_encontrado
                                usuario_existente.nombre = nombre
                                usuario_existente.ci = ci
                                usuario_existente.zona = zona
                                usuario_existente.nro_medidor = nro_medidor
                                usuario_existente.categoria = categoria
                                sess.add(usuario_existente)
                                sess.commit()
                                st.success("Usuario actualizado exitosamente")
                            else:
                                existe = sess.exec(
                                    select(Usuario).where(Usuario.epsa_id == epsa_id, Usuario.codigo == codigo)
                                ).first()
                                if existe:
                                    st.error(f"El código {codigo} ya existe. Usa la búsqueda para editar.")
                                else:      #Aqui se ha agregado el try except para verificacion de limite de usuarios
                                    try:
                                        verificar_limite_usuarios(epsa_id)
                                        create_usuario(sess, epsa_id, codigo, nombre, ci, zona, nro_medidor, categoria) #original
                                        st.success("Usuario creado exitosamente")
                                    except LimiteExcedidoError as e:
                                        st.error(str(e))
                                        return None

                            st.session_state.editando = False
                            st.session_state.usuario_encontrado = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    # ---------- TAB 3: Importar desde Excel ----------
    with tab3:
        st.markdown("""
        **Formato del archivo Excel requerido (.xlsx)**
        Debe tener las siguientes columnas (en cualquier orden):
        - `codigo` (texto, único por EPSA)
        - `nombre`
        - `ci`
        - `zona`
        - `nro_medidor`
        - `categoria` (opcional, por defecto RESIDENCIAL)
        """)
        uploaded_file = st.file_uploader("Subir archivo Excel", type=["xlsx"])
        if uploaded_file:
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name
            try:
                with st.spinner("Procesando archivo..."):
                    with get_session() as sess:
                        resultado = importar_usuarios_desde_excel(sess, epsa_id, tmp_path)
                st.write(f"**Total procesado:** {resultado['total']}")
                st.write(f"**Insertados:** {resultado['insertados']}")
                if resultado['errores']:
                    st.error(f"**Errores:** {len(resultado['errores'])}")
                    with st.expander("Ver detalles de errores"):
                        for err in resultado['errores'][:50]:
                            st.text(err)
                else:
                    st.success("✅ Todos los usuarios fueron importados correctamente")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
            finally:
                os.unlink(tmp_path)