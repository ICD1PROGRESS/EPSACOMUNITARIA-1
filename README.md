# 💧 EPSACOMUNITARIA Digital

**Sistema de Gestión Integral de Agua Potable para Entidades Prestadoras de Servicios de Agua (EPSAs)**

[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?style=flat&logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue?style=flat&logo=postgresql)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Descripción

**EPSACOMUNITARIA Digital** es una plataforma web diseñada para la gestión integral de servicios de agua potable en municipios, conforme a la **Ley N° 2066 de Bolivia**. Permite administrar usuarios, lecturas de medidores, tarifas por rangos, pagos, deudas, periodos de facturación y generar reportes ejecutivos.

Ideal para **EPSAs municipales, cooperativas de agua, entidades prestadoras y Consultores DESCOM** que buscan digitalizar sus procesos, reducir tiempos de facturación y mejorar la transparencia en la recaudación.

El proyecto nace como evolución de una herramienta desarrollada originalmente en Microsoft Excel con VBA, utilizada durante varios años en operaciones reales en el municipio de Colquiri, migrando posteriormente a una plataforma web moderna utilizando Python.

---

# 🎯 Objetivos

✔ Digitalizar procesos administrativos
✔ Reducir errores de cálculo
✔ Mejorar la recaudación
✔ Centralizar información
✔ Facilitar la toma de decisiones
✔ Modernizar la gestión municipal

---

## 📚 Documentación

- 📖 **[Manual de Usuario](docs/manual_epsacomunitaria.pdf)** – Guía completa para administradores y operadores.

---

## 🚀 Características principales

| Módulo | Funcionalidad |
|--------|---------------|
| **👥 Gestión de Usuarios** | Padrón completo, importación desde Excel, categorías (residencial, comercial, industrial). |
| **💰 Tarifas por Rangos** | Configuración flexible según consumo (Ley 2066), con cargo fijo y precios escalonados. |
| **📝 Toma de Lecturas** | Registro manual o masivo de medidores, cálculo automático de consumo e importe. |
| **💵 Caja / Pagos** | Cobros con generación de recibos PDF (dos por hoja: cliente y copia), control de cambio. |
| **📊 Deudas y Cartera** | Gestión de morosidad, reconexiones, saldo acumulado por usuario. |
| **🔄 Cierre de Periodo** | Facturación mensual/bimestral, generación automática de deudas y nuevo período. |
| **📈 Reportes** | Recaudación, consumo, morosidad, estado de cuentas. |
| **⚙️ Multi-EPSA** | Soporte para múltiples entidades desde una sola instalación (super_admin). |
| **🔐 Control de Acceso** | Roles: super_admin, admin_epsa, cajero. |
| **📱 Responsive** | Acceso desde cualquier dispositivo (PC, tablet, móvil). |

---

## 🖼️ Capturas de pantalla

### Dashboard principal
![Dashboard](screenshots/dashboard.png)

---

## 🛠️ Tecnologías utilizadas

- **Frontend**: [Streamlit](https://streamlit.io) – interfaces interactivas en Python.
- **Backend**: Python 3.10+ con SQLModel (ORM) y SQLAlchemy.
- **Base de datos**: PostgreSQL (Neon.tech o Supabase) – plan gratuito disponible.
- **Reportes PDF**: ReportLab – generación de recibos profesionales.
- **Visualización**: Plotly y Pandas – gráficos interactivos.
- **Autenticación**: Hash SHA256 con salt – seguro y sin dependencias externas.
- **Almacenamiento**: Neon.tech (PostgreSQL en la nube) con pooler para alta disponibilidad.

---

## 📦 Instalación y pruebas

[Demo en Streamlit](https://epsacomunitaria-1-ilyfoz5xepmm7szftxktqe.streamlit.app/)

---

## 👥 Créditos y contacto
Desarrollado por Macario Esprella
	Ingeniero Agronomo
	Especialista en Gestión del Agua
	Python Developer
	Transformación Digital para Municipios
    📧 Email: esprellamacario@gmail.com


## 🏛️ Soporte para EPSAs
¿Eres una EPSA municipal y necesitas implementar el sistema?
Ofrecemos:

    Implementación personalizada (migración de datos, configuración).
    Capacitación presencial o virtual para el personal.
    Soporte técnico prioritario (chat, teléfono, email).
    Planes de suscripción adaptados a tu tamaño y necesidades.

---

# ⭐ Si este proyecto te resulta útil

No olvides dejar una ⭐ en GitHub.
Tu apoyo ayuda a continuar desarrollando soluciones tecnológicas para fortalecer la gestión pública y los servicios de agua potable.

---

**¡Digitaliza tu gestión del agua con EPSACOMUNITARIA Digital!** 💧🚀
