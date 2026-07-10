import streamlit as st
from datetime import date
from sqlmodel import select, func
from src.database.connection import get_session
from src.database.models import Usuario, Lectura, Pago, ConfiguracionEPSA, Deuda
from src.database.crud import get_periodo_activo_nombre, get_pago_by_usuario_periodo
from src.utils.recibo_pdf import generar_recibo_pdf
from pathlib import Path

def show():
    st.title("💵 Caja - Registro de Pagos")
    st.caption("Sistema de Gestión Integral de Agua Potable Comunitaria")

    epsa_id = st.session_state.get("epsa_id")
    if not epsa_id:
        st.warning("⚠️ Primero selecciona una EPSA en el panel lateral.")
        return

    # ------------------------------------------------------------------
    # MENSAJES FLASH (después de st.rerun)
    # ------------------------------------------------------------------
    if "caja_mensaje" in st.session_state:
        msg = st.session_state.caja_mensaje
        if msg["tipo"] == "success":
            st.success(msg["texto"])
        elif msg["tipo"] == "error":
            st.error(msg["texto"])
        if msg.get("pdf_ruta") and Path(msg["pdf_ruta"]).exists():
            with open(msg["pdf_ruta"], "rb") as f:
                st.download_button(
                    label="📄 Descargar Recibo PDF",
                    data=f,
                    file_name=msg.get("pdf_nombre", "recibo.pdf"),
                    mime="application/pdf"
                )
        del st.session_state.caja_mensaje


    # ------------------------------------------------------------------
    # 1. BÚSQUEDA DE CLIENTE (ccli_Change + Lcliente1)
    # ------------------------------------------------------------------
    st.subheader("🔍 Buscar usuario")
    st.markdown("Escriba código o nombre y presione **ENTER** para buscar")

    search_term = st.text_input(
        "Código o nombre",
        placeholder="Ej: AP-001 o GONZALES",
        key="caja_search_term"
    )

    # Buscar automáticamente cuando el término cambia y no está vacío
    if search_term and search_term != st.session_state.get("caja_search_term_anterior", ""):
        with get_session() as session:
            # SQLite es case-insensitive por defecto en LIKE, no necesita func.upper()
            usuarios = session.exec(
                select(Usuario)
                .where(Usuario.epsa_id == epsa_id)
                .where(
                    (Usuario.codigo.contains(search_term)) |
                    (Usuario.nombre.contains(search_term))
                )
            ).all()
        st.session_state.caja_resultados_busqueda = usuarios
        st.session_state.caja_usuario_seleccionado = None
        st.session_state.caja_search_term_anterior = search_term

    if "caja_resultados_busqueda" in st.session_state:
        resultados = st.session_state.caja_resultados_busqueda
        if not resultados:
            st.warning("No se encontraron usuarios con ese criterio.")
        else:
            opciones = {f"{u.codigo}  |  {u.nombre}  |  {u.zona}": u for u in resultados}
            sel = st.selectbox("Seleccione usuario", list(opciones.keys()), key="caja_sel_usuario")
            if st.button("📋 Cargar datos del cliente", type="primary"):
                st.session_state.caja_usuario_seleccionado = opciones[sel]
                st.rerun()
    # ------------------------------------------------------------------
    # 2. DATOS DEL CLIENTE CARGADO (Lcliente1_DblClick)
    # ------------------------------------------------------------------
    if not st.session_state.get("caja_usuario_seleccionado"):
        return

    usuario = st.session_state.caja_usuario_seleccionado

    with get_session() as session:
        # Refrescar desde BD
        usuario_db = session.get(Usuario, usuario.id)
        if not usuario_db:
            st.error("Usuario no encontrado en base de datos.")
            return

        # PERIODO ACTIVO: usa fallback a última lectura si no hay tabla Periodo
        nombre_periodo = get_periodo_activo_nombre(session, epsa_id)

        # Lectura del periodo activo
        lectura = session.exec(
            select(Lectura)
            .where(Lectura.usuario_id == usuario_db.id)
            .where(Lectura.periodo == nombre_periodo)
        ).first()

        # ¿Ya pagó este periodo? (columna O=1 en macro)
        pago_existente = None
        if lectura:
            pago_existente = get_pago_by_usuario_periodo(session, usuario_db.id, nombre_periodo)

        # Deudas pendientes (hoja deuda + resdeu)
        deudas = session.exec(
            select(Deuda)
            .where(Deuda.usuario_id == usuario_db.id)
            .where(Deuda.estado == "PENDIENTE")
            .order_by(Deuda.id)
        ).all()

    # --- Layout datos cliente (estilo recibo D6-D9, L9) ---
    st.markdown("---")
    st.subheader("📋 Datos del Cliente")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Código", value=usuario_db.codigo, disabled=True)
        st.text_input("Nombre", value=usuario_db.nombre, disabled=True)
        st.text_input("C.I.", value=usuario_db.ci, disabled=True)
    with col2:
        st.text_input("Zona", value=usuario_db.zona, disabled=True)
        st.text_input("N° Medidor", value=usuario_db.nro_medidor, disabled=True)
        st.text_input("Periodo activo", value=nombre_periodo, disabled=True)

    # Aviso si ya pagó (estado O=1)
    if pago_existente:
        st.warning("⚠️ **ESTE USUARIO YA HA CANCELADO SU CONSUMO DEL PERIODO**")

    # --- Lectura (estilo K11, K12, L13) ---
    st.markdown("---")
    st.subheader("📖 Lectura del Periodo")

    if lectura:
        c1, c2, c3 = st.columns(3)
        c1.metric("Lectura Anterior", f"{lectura.lectura_anterior:.2f}")
        c2.metric("Lectura Actual", f"{lectura.lectura_actual:.2f}")
        c3.metric("Consumo", f"{lectura.consumo_m3:.2f} m³")

        importe_periodo = lectura.importe_calculado or 0.0
        st.metric("💵 Importe calculado del consumo", f"{importe_periodo:.2f} Bs")
    else:
        st.info("No existe lectura registrada para este periodo.")
        importe_periodo = 0.0

    # --- Deudas pendientes (resdeu / Deudas.frm) ---
    st.markdown("---")
    st.subheader("📋 Deudas Pendientes")

    total_deudas = 0.0
    if deudas:
        filas = []
        for d in deudas:
            filas.append({
                "N° Deuda": d.nro_deuda,
                "Período": d.periodo,
                "Consumo (m³)": f"{d.consumo_m3:.2f}" if d.consumo_m3 else "-",
                "Monto (Bs)": f"{d.monto:.2f}",
                "Vence": d.fecha_vencimiento.strftime("%d/%m/%Y") if d.fecha_vencimiento else "-"
            })
            total_deudas += d.monto
        st.dataframe(filas, use_container_width=True, hide_index=True)
        st.metric("💸 Total Deudas Anteriores", f"{total_deudas:.2f} Bs")
    else:
        st.info("El usuario no tiene deudas pendientes.")

    # --- Resumen de pago (importe + deuda + reconexión = total) ---
    st.markdown("---")
    st.subheader("💰 Resumen de Pago")

    incluir_reconexion = st.checkbox("Incluir cargo por Reconexión", value=False, key="caja_chk_recon")
    cargo_reconexion = 0.0
    if incluir_reconexion:
        cargo_reconexion = st.number_input("Monto Reconexión (Bs)", min_value=0.0, value=20.0, step=5.0, key="caja_monto_recon")

    total_a_pagar = importe_periodo + total_deudas + cargo_reconexion

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("Importe Periodo", f"{importe_periodo:.2f} Bs")
    col_r2.metric("Deudas", f"{total_deudas:.2f} Bs")
    col_r3.metric("TOTAL A PAGAR", f"{total_a_pagar:.2f} Bs",
                  delta=f"+{cargo_reconexion:.2f} Recon." if cargo_reconexion > 0 else None)

    # ------------------------------------------------------------------
    # 3. PAGO TOTAL (pagar_Click)
    # ------------------------------------------------------------------
    if total_a_pagar > 0 and (not pago_existente or total_deudas > 0):
        st.markdown("---")
        st.subheader("🧾 Pago Total")

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            efectivo = st.number_input("Efectivo recibido (Bs)", min_value=0.0, step=1.0, format="%.2f", key="caja_efectivo")
        with col_e2:
            cambio = efectivo - total_a_pagar
            if efectivo > 0:
                color = "normal" if cambio >= 0 else "inverse"
                st.metric("Cambio a entregar", f"{cambio:.2f} Bs",
                          delta="Completo" if cambio >= 0 else "Falta efectivo")
            else:
                st.write("Ingrese efectivo")

        if st.button("✅ REGISTRAR PAGO E IMPRIMIR RECIBO", type="primary", use_container_width=True):
            if efectivo < total_a_pagar:
                st.error("❌ El efectivo recibido es menor al total a pagar.")
                return
                
            try:
                with get_session() as session:
                    usuario_db = session.get(Usuario, usuario.id)
                    lectura_db = session.exec(
                        select(Lectura).where(Lectura.usuario_id == usuario.id, Lectura.periodo == nombre_periodo)
                    ).first()

                    # N° recibo autoincremental
                    max_id = session.exec(select(func.max(Pago.id))).first() or 0
                    nro_recibo = f"REC-{date.today().strftime('%Y')}-{max_id + 1}"

                    # 1) OBTENER DEUDAS FRESAS DE LA BD
                    deudas_db = session.exec(
                        select(Deuda)
                        .where(Deuda.usuario_id == usuario.id)
                        .where(Deuda.estado == "PENDIENTE")
                        .order_by(Deuda.id)
                    ).all()

                    # Recalcular totales desde la BD para evitar inconsistencias
                    total_deudas_fresco = round(sum(d.monto for d in deudas_db), 2)
                    importe_periodo_fresco = round(lectura_db.importe_calculado, 2) if lectura_db else 0.0
                    cargo_reconexion_redondeado = round(cargo_reconexion, 2)
                    
                    total_a_pagar_fresco = round(importe_periodo_fresco + total_deudas_fresco + cargo_reconexion_redondeado, 2)
                    efectivo_redondeado = round(efectivo, 2)

                    # CORRECCIÓN: el cambio se calcula con los valores frescos de la transacción
                    cambio_fresco = round(efectivo_redondeado - total_a_pagar_fresco, 2)

                    # Validación con tolerancia de 0.01 Bs
                    if efectivo_redondeado + 0.01 < total_a_pagar_fresco:
                        st.error(f"❌ El efectivo ({efectivo_redondeado:.2f}) es menor al total ({total_a_pagar_fresco:.2f}).")
                        return

                    # 2) PAGAR DEUDAS (más antiguas primero)
                    monto_restante = round(total_a_pagar_fresco - cargo_reconexion_redondeado, 2)

                    for deuda in deudas_db:
                        if monto_restante <= 0.01: 
                            break
                        monto_deuda = round(deuda.monto, 2)
                        if monto_restante + 0.01 >= monto_deuda:
                            deuda.estado = "PAGADO"
                            monto_restante = round(monto_restante - monto_deuda, 2)
                            session.add(deuda)
                        else:
                            st.warning(f"El monto no alcanza para pagar la deuda {deuda.nro_deuda} completa. Operación cancelada.")
                            session.rollback()
                            return

                    # 3) PAGAR PERIODO ACTUAL
                    if lectura_db and importe_periodo_fresco > 0 and not pago_existente:
                        if monto_restante + 0.01 >= importe_periodo_fresco:
                            monto_restante = round(monto_restante - importe_periodo_fresco, 2)
                        else:
                            st.warning(f"El monto no alcanza para cubrir el consumo del periodo. "
                                     f"(Restante: {monto_restante:.2f}, Consumo: {importe_periodo_fresco:.2f})")
                            session.rollback()
                            return

                    # 4) REGISTRAR PAGO
                    pago_total = Pago(
                        epsa_id=epsa_id,
                        usuario_id=usuario.id,
                        fecha_pago=date.today(),
                        monto=total_a_pagar_fresco,  # ✅ SOLO el monto real pagado, sin el cambio
                        periodo=nombre_periodo,
                        recibo_nro=nro_recibo
                    )
                    session.add(pago_total)

                    # 5) ACTUALIZAR SALDO
                    # Solo se descuenta lo que se aplicó a deuda + consumo (no reconexión)
                    monto_aplicado = round(total_a_pagar_fresco - cargo_reconexion_redondeado - monto_restante, 2)
                    usuario_db.saldo_actual = max(0.0, round(usuario_db.saldo_actual - monto_aplicado, 2))
                    session.add(usuario_db)
                    session.commit()

                    # 6) GENERAR RECIBO PDF
                    config = session.exec(
                        select(ConfiguracionEPSA).where(ConfiguracionEPSA.epsa_id == epsa_id)
                    ).first()

                    datos_recibo = {
                        'codigo': usuario_db.codigo,
                        'nombre': usuario_db.nombre,
                        'ci': usuario_db.ci,
                        'zona': usuario_db.zona,
                        'medidor': usuario_db.nro_medidor,
                        'periodo': nombre_periodo,
                        'lectura_anterior': lectura_db.lectura_anterior if lectura_db else 0,
                        'lectura_actual': lectura_db.lectura_actual if lectura_db else 0,
                        'consumo': lectura_db.consumo_m3 if lectura_db else 0,
                        'importe_consumo': importe_periodo_fresco,        # ✅ Valor fresco de BD
                        'reconexion': cargo_reconexion_redondeado,        # ✅ Valor redondeado
                        'deuda': total_deudas_fresco,                     # ✅ Valor fresco de BD
                        'total': total_a_pagar_fresco,                    # ✅ Total real pagado
                        'nro_recibo': nro_recibo,
                        'fecha': date.today(),
                        'efectivo': efectivo_redondeado,                  # ✅ Efectivo recibido
                        'cambio': cambio_fresco,                          # ✅ Cambio calculado fresco
                        'es_deuda_especifica': False
                    }

                    ruta_pdf = generar_recibo_pdf(usuario_db, datos_recibo, config)

                    # Preparar mensaje flash y LIMPIAR formulario
                    st.session_state.caja_mensaje = {
                        "tipo": "success",
                        "texto": f"✅ Pago registrado. Recibo {nro_recibo}. Cambio: {cambio_fresco:.2f} Bs",
                        "pdf_ruta": ruta_pdf,
                        "pdf_nombre": f"recibo_{usuario_db.codigo}_{date.today()}.pdf"
                    }

                    # Limpiar solo lo que NO es un widget de texto instanciado arriba
                    st.session_state.caja_usuario_seleccionado = None
                    st.session_state.caja_resultados_busqueda = []

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al procesar el pago: {e}")

    # ------------------------------------------------------------------
    # 4. PAGO DE DEUDA ESPECÍFICA (dpag_Click de Deudas.frm)
    # ------------------------------------------------------------------
    if deudas:
        st.markdown("---")
        st.subheader("📌 Pago de Deuda Específica")

        opciones_deuda = {f"{d.nro_deuda}  |  {d.periodo}  |  {d.monto:.2f} Bs": d for d in deudas}
        sel_deuda_str = st.selectbox("Seleccione la deuda a pagar", list(opciones_deuda.keys()), key="caja_sel_deuda")

        if sel_deuda_str:
            deuda_sel = opciones_deuda[sel_deuda_str]

            if st.button("💵 PAGAR DEUDA SELECCIONADA", type="secondary", use_container_width=True):
                try:
                    with get_session() as session:
                        usuario_db = session.get(Usuario, usuario.id)
                        deuda_db = session.get(Deuda, deuda_sel.id)

                        if not deuda_db or deuda_db.estado != "PENDIENTE":
                            st.error("La deuda ya no está disponible.")
                            return

                        max_id = session.exec(select(func.max(Pago.id))).first() or 0
                        nro_recibo_d = f"REC-D{date.today().strftime('%Y%m%d')}-{max_id + 1}"

                        pago_d = Pago(
                            epsa_id=epsa_id,
                            usuario_id=usuario.id,
                            fecha_pago=date.today(),
                            monto=deuda_db.monto,
                            periodo=deuda_db.periodo,
                            recibo_nro=nro_recibo_d
                        )
                        session.add(pago_d)

                        deuda_db.estado = "PAGADO"
                        session.add(deuda_db)

                        usuario_db.saldo_actual = max(0.0, usuario_db.saldo_actual - deuda_db.monto)
                        session.add(usuario_db)
                        session.commit()

                        config = session.exec(
                            select(ConfiguracionEPSA).where(ConfiguracionEPSA.epsa_id == epsa_id)
                        ).first()

                        datos_recibo_d = {
                            'codigo': usuario_db.codigo,
                            'nombre': usuario_db.nombre,
                            'ci': usuario_db.ci,
                            'zona': usuario_db.zona,
                            'medidor': usuario_db.nro_medidor,
                            'periodo': deuda_db.periodo,
                            'lectura_anterior': "-",
                            'lectura_actual': "-",
                            'consumo': deuda_db.consumo_m3 if deuda_db.consumo_m3 else 0,
                            'importe_consumo': deuda_db.monto,
                            'reconexion': 0,
                            'deuda': 0,
                            'total': deuda_db.monto,
                            'nro_recibo': nro_recibo_d,
                            'fecha': date.today(),
                            'efectivo': deuda_db.monto,
                            'cambio': 0,
                            'es_deuda_especifica': True
                        }

                        ruta_pdf_d = generar_recibo_pdf(usuario_db, datos_recibo_d, config)

                        st.session_state.caja_mensaje = {
                            "tipo": "success",
                            "texto": f"✅ Deuda {deuda_db.nro_deuda} pagada. Recibo {nro_recibo_d}",
                            "pdf_ruta": ruta_pdf_d,
                            "pdf_nombre": f"recibo_deuda_{deuda_db.nro_deuda}_{date.today()}.pdf"
                        }

                        st.session_state.caja_usuario_seleccionado = None
                        st.session_state.caja_resultados_busqueda = []

                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error al pagar deuda: {e}")