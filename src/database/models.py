# src/database/models.py
from sqlmodel import SQLModel, Field, Relationship
from datetime import date, datetime
from typing import Optional, List
from enum import Enum

# ============================================================
# MODELOS BASE (sin dependencias)
# ============================================================

class EPSA(SQLModel, table=True):
    __tablename__ = "epsas"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True)
    ciudad: str
    created_at: datetime = Field(default_factory=datetime.now)

    usuarios: List["Usuario"] = Relationship(back_populates="epsa")
    tarifas: List["Tarifa"] = Relationship(back_populates="epsa")
    lecturas: List["Lectura"] = Relationship(back_populates="epsa")
    pagos: List["Pago"] = Relationship(back_populates="epsa")
    configuracion: Optional["ConfiguracionEPSA"] = Relationship(back_populates="epsa")
    deudas: List["Deuda"] = Relationship(back_populates="epsa")
    suscripcion: Optional["Suscripcion"] = Relationship(back_populates="epsa")


class ConfiguracionEPSA(SQLModel, table=True):
    __tablename__ = "configuracion_epsa"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id", unique=True)
    logo_path: Optional[str] = None
    membrete_texto: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sitio_web: Optional[str] = None

    epsa: EPSA = Relationship(back_populates="configuracion")


class Tarifa(SQLModel, table=True):
    __tablename__ = "tarifas"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    rango_inicio: float
    rango_fin: Optional[float] = None
    precio_unitario: float
    cargo_fijo: float = 0.0
    orden: int = 0

    epsa: EPSA = Relationship(back_populates="tarifas")


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    codigo: str = Field(index=True)
    nombre: str
    ci: str
    zona: str
    nro_medidor: str
    categoria: str = Field(default="RESIDENCIAL")
    saldo_actual: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.now)

    epsa: EPSA = Relationship(back_populates="usuarios")
    lecturas: List["Lectura"] = Relationship(back_populates="usuario")
    pagos: List["Pago"] = Relationship(back_populates="usuario")
    deudas: List["Deuda"] = Relationship(back_populates="usuario")


class Lectura(SQLModel, table=True):
    __tablename__ = "lecturas"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    usuario_id: int = Field(foreign_key="usuarios.id")
    periodo: str
    lectura_anterior: float
    lectura_actual: float
    consumo_m3: float
    fecha_toma: date
    importe_calculado: float = 0.0

    usuario: "Usuario" = Relationship(back_populates="lecturas")
    epsa: EPSA = Relationship(back_populates="lecturas")


class Pago(SQLModel, table=True):
    __tablename__ = "pagos"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    usuario_id: int = Field(foreign_key="usuarios.id")
    fecha_pago: date
    monto: float
    periodo: str
    recibo_nro: str
    created_at: datetime = Field(default_factory=datetime.now)

    usuario: Usuario = Relationship(back_populates="pagos")
    epsa: EPSA = Relationship(back_populates="pagos")


class Deuda(SQLModel, table=True):
    __tablename__ = "deudas"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    usuario_id: int = Field(foreign_key="usuarios.id")
    nro_deuda: str
    periodo: str
    consumo_m3: Optional[float] = None
    monto: float
    estado: str = Field(default="PENDIENTE")
    fecha_vencimiento: Optional[date] = None

    usuario: "Usuario" = Relationship(back_populates="deudas")
    epsa: "EPSA" = Relationship(back_populates="deudas")


class Periodo(SQLModel, table=True):
    __tablename__ = "periodos"
    #__table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool = Field(default=True)
    cerrado: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# MODELOS DE SUSCRIPCIONES (nuevos)
# ============================================================

class EstadoSuscripcion(str, Enum):
    TRIAL = "trial"
    ACTIVA = "activa"
    VENCIDA = "vencida"
    CANCELADA = "cancelada"

class Plan(SQLModel, table=True):
    __tablename__ = "planes"
    #__table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    precio_mensual_usd: float
    max_usuarios: int
    max_epsas: int
    max_cajeros: int
    tiene_reportes_avanzados: bool = False
    tiene_backup: bool = False
    tiene_api: bool = False
    soporte_nivel: str = Field(default="email")
    
    suscripciones: List["Suscripcion"] = Relationship(back_populates="plan")


class Suscripcion(SQLModel, table=True):
    __tablename__ = "suscripciones"
    #__table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    epsa_id: int = Field(foreign_key="epsas.id")
    plan_id: int = Field(foreign_key="planes.id")
    
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    estado: EstadoSuscripcion = Field(default=EstadoSuscripcion.TRIAL)
    
    monto_pagado_mes: float = Field(default=0.0)
    metodo_pago: Optional[str] = None
    comprobante_url: Optional[str] = None
    
    descuento_porcentaje: int = Field(default=0)
    
    epsa: Optional[EPSA] = Relationship(back_populates="suscripcion")
    plan: Optional[Plan] = Relationship(back_populates="suscripciones")


class PagoSuscripcion(SQLModel, table=True):
    __tablename__ = "pago_suscripcion"
    #__table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    suscripcion_id: int = Field(foreign_key="suscripciones.id")
    fecha: datetime = Field(default_factory=datetime.now)
    monto: float
    metodo: str
    estado: str = Field(default="pendiente")
    referencia: Optional[str] = None

class UsuarioSistema(SQLModel, table=True):
    __tablename__ = "usuarios_sistema"
    #__table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    salt: str
    role: str = Field(default="cajero")
    epsa_id: Optional[int] = Field(default=None, foreign_key="epsas.id")
    nombre_completo: str = Field(default="")
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)