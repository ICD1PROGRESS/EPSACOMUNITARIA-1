import streamlit as st
import pandas as pd
from sqlmodel import Session, select
from src.database.connection import get_session
from src.database.models import Tarifa
from src.database.crud import get_tarifas_by_epsa, delete_tarifa

def show():
    st.title("💰 Configuración de Tarifas por Rangos (Ley 2066)")
    epsa_id = st.session_state.get("epsa_id")
    if not epsa_id:
        st.warning("Primero selecciona o crea una EPSA.")
        return

    with get_session() as session:
        tarifas = get_tarifas_by_epsa(session, epsa_id)

    st.subheader("Rangos actuales")
    if tarifas:
        data = []
        for t in tarifas:
            rango = f"{t.rango_inicio:.2f} - {t.rango_fin:.2f}" if t.rango_fin else f"{t.rango_inicio:.2f} en adelante"
            data.append({
                "Orden": t.orden,
                "Rango (m³)": rango,
                "Precio (Bs/m³)": t.precio_unitario,
                "Cargo fijo (Bs)": t.cargo_fijo,
                "ID": t.id
            })
        df = pd.DataFrame(data).sort_values("Orden")
        st.table(data)
        #st.dataframe(df, use_container_width=True)

        # Eliminar rango
        with st.expander("🗑️ Eliminar un rango"):
            id_eliminar = st.selectbox("Seleccionar ID del rango a eliminar", [t.id for t in tarifas])
            if st.button("Eliminar rango", type="primary"):
                with get_session() as sess:
                    delete_tarifa(sess, id_eliminar)
                st.success("Rango eliminado")
                st.rerun()
    else:
        st.info("No hay rangos configurados. Usa el formulario para agregar.")

    st.subheader("Agregar / Modificar rangos")
    with st.form("tarifa_form"):
        col1, col2 = st.columns(2)
        with col1:
            rango_inicio = st.number_input("Inicio del rango (m³)", min_value=0.0, step=0.1)
            precio = st.number_input("Precio unitario (Bs/m³)", min_value=0.0, step=0.1)
        with col2:
            rango_fin = st.number_input("Fin del rango (m³) – dejar vacío para infinito", min_value=0.0, step=0.1, value=None)
            cargo_fijo = st.number_input("Cargo fijo (solo primer rango)", min_value=0.0, step=1.0, value=0.0)
        orden = st.number_input("Orden (0,1,2...)", min_value=0, step=1, value=len(tarifas))
        submit = st.form_submit_button("Guardar rango")

        if submit:
            if rango_inicio is None:
                st.error("El inicio del rango es obligatorio")
            else:
                with get_session() as sess:
                    # Validar que no haya rangos superpuestos
                    existentes = sess.exec(select(Tarifa).where(Tarifa.epsa_id == epsa_id)).all()
                    for ex in existentes:
                        if ex.rango_inicio == rango_inicio:
                            st.error(f"Ya existe un rango que inicia en {rango_inicio} m³")
                            st.stop()
                    nueva = Tarifa(
                        epsa_id=epsa_id,
                        rango_inicio=rango_inicio,
                        rango_fin=rango_fin,
                        precio_unitario=precio,
                        cargo_fijo=cargo_fijo,
                        orden=orden
                    )
                    sess.add(nueva)
                    sess.commit()
                st.success("Rango agregado")
                st.rerun()

    # Botón para cargar rangos por defecto (basado en tu macro original)
    if st.button("📋 Cargar rangos por defecto"):
        with get_session() as sess:
            # Eliminar rangos existentes de esta EPSA
            existentes = sess.exec(select(Tarifa).where(Tarifa.epsa_id == epsa_id)).all()
            for ex in existentes:
                sess.delete(ex)
            # Rangos originales (ajusta precios si quieres)
            rangos_defecto = [
                (0.0, 1.375, 0.0, 20.0, 0),      # rango1: cargo fijo 20, precio 0 (no aplica)
                (1.375, 3.5, 16.04, 0.0, 1),     # rango2: precio 14.54+1.5 = 16.04
                (3.5, 10.0, 16.54, 0.0, 2),      # rango3: precio 14.54+2 = 16.54
                (10.0, None, 17.54, 0.0, 3)      # rango4: precio 14.54+3 = 17.54
            ]
            for inicio, fin, precio, fijo, orden in rangos_defecto:
                sess.add(Tarifa(
                    epsa_id=epsa_id,
                    rango_inicio=inicio,
                    rango_fin=fin,
                    precio_unitario=precio,
                    cargo_fijo=fijo,
                    orden=orden
                ))
            sess.commit()
        st.success("Rangos por defecto cargados. Revisa la tabla.")
        st.rerun()

    st.caption("💡 **Nota:** El primer rango debe tener `cargo_fijo` > 0 y `precio_unitario` puede ser 0. Los rangos se evalúan en orden ascendente.")