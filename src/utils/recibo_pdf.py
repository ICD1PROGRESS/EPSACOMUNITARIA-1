# src/utils/recibo_pdf.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, HRFlowable, FrameBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from pathlib import Path
from datetime import date, timedelta


def numero_a_letras(numero):
    """Convierte un número a letras en español."""
    if numero is None or numero == 0:
        return "CERO 00/100 BOLIVIANOS"
    
    unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    especiales = {11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE",
                  16: "DIECISEIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE"}
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
    
    def convertir_entero(n):
        if n == 0:
            return "CERO"
        if n == 100:
            return "CIEN"
        if n < 10:
            return unidades[n]
        if 10 < n < 20:
            return especiales.get(n, "")
        if n < 100:
            d, u = divmod(n, 10)
            if u == 0:
                return decenas[d]
            return f"{decenas[d]} Y {unidades[u]}"
        if n < 1000:
            c, resto = divmod(n, 100)
            if resto == 0:
                return centenas[c]
            return f"{centenas[c]} {convertir_entero(resto)}"
        if n < 1000000:
            m, resto = divmod(n, 1000)
            if m == 1:
                prefijo = "MIL"
            else:
                prefijo = f"{convertir_entero(m)} MIL"
            if resto == 0:
                return prefijo
            return f"{prefijo} {convertir_entero(resto)}"
        return str(n)
    
    entero = int(numero)
    decimal = int(round((numero - entero) * 100))
    
    letras = convertir_entero(entero)
    return f"{letras} {decimal:02d}/100 BOLIVIANOS"

def _crear_contenido_recibo(usuario, datos_recibo, config_epsa, styles):
    """
    Construye la lista de flowables para un solo recibo.
    Versión ultra-compacta para que quepan 2 recibos en una hoja carta.
    """
    # Estilos ultra-reducidos
    style_titulo = ParagraphStyle(
        'TituloRecibo',
        parent=styles['Heading1'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=1,
        textColor=colors.HexColor('#1a5276'),
        fontName='Helvetica-Bold'
    )
    
    style_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        spaceAfter=2,
        textColor=colors.HexColor('#5d6d7e')
    )
    
    style_seccion = ParagraphStyle(
        'Seccion',
        parent=styles['Heading3'],
        fontSize=7,
        textColor=colors.HexColor('#1a5276'),
        spaceAfter=1,
        spaceBefore=2,
        fontName='Helvetica-Bold'
    )
    
    style_label = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#5d6d7e'),
        fontName='Helvetica-Bold',
        leading=7
    )
    
    style_valor = ParagraphStyle(
        'Valor',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.black,
        fontName='Helvetica',
        leading=7
    )
    
    style_total = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#1a5276'),
        fontName='Helvetica-Bold',
        leading=9
    )
    
    style_son = ParagraphStyle(
        'Son',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.black,
        fontName='Helvetica-Oblique',
        leading=7
    )
    
    style_firma = ParagraphStyle(
        'Firma',
        parent=styles['Normal'],
        fontSize=5,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#5d6d7e'),
        fontName='Helvetica',
        leading=6
    )

    story = []

    # Logo
    logo_img = None
    if config_epsa and config_epsa.logo_path:
        logo_path = Path(config_epsa.logo_path)
        if logo_path.exists():
            try:
                logo_img = Image(str(logo_path), width=0.5*inch, height=0.4*inch)
            except Exception:
                logo_img = None

    membrete = config_epsa.membrete_texto if (config_epsa and config_epsa.membrete_texto) else "EPSA MUNICIPAL"

    # Encabezado
    titulo_central = Paragraph(
        f"<b>{membrete}</b><br/><font size=10 color='#1a5276'>R E C I B O        O F I C I A L</font>",
        style_subtitulo
    )
    nro_recibo_text = Paragraph(
        f"<b>RECIBO N°:</b><br/><font size=8>{datos_recibo['nro_recibo']}</font>",
        style_valor
    )

    header_data = []
    if logo_img:
        header_data.append([logo_img, titulo_central, nro_recibo_text])
    else:
        header_data.append(["", titulo_central, nro_recibo_text])

    t_header = Table(header_data, colWidths=[0.7*inch, 4.6*inch, 1.7*inch])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#1a5276')))
    story.append(Spacer(1, 2))

    # Datos del cliente
    story.append(Paragraph("DATOS DEL CLIENTE", style_seccion))

    fecha_emision = datos_recibo['fecha'].strftime('%d/%m/%Y')
    fecha_venc = datos_recibo['fecha'] + timedelta(days=30)
    fecha_venc_str = fecha_venc.strftime('%d/%m/%Y')

    datos_izq = [
        [Paragraph("<b>Código:</b>", style_label), Paragraph(datos_recibo['codigo'], style_valor)],
        [Paragraph("<b>Nombre:</b>", style_label), Paragraph(datos_recibo['nombre'], style_valor)],
        [Paragraph("<b>NIT / C.I.:</b>", style_label), Paragraph(datos_recibo['ci'], style_valor)],
    ]
    datos_der = [
        [Paragraph("<b>Emisión:</b>", style_label), Paragraph(fecha_emision, style_valor)],
        [Paragraph("<b>Período:</b>", style_label), Paragraph(datos_recibo['periodo'], style_valor)],
        [Paragraph("<b>Vence:</b>", style_label), Paragraph(fecha_venc_str, style_valor)],
    ]

    filas_combinadas = []
    for i in range(max(len(datos_izq), len(datos_der))):
        izq = datos_izq[i] if i < len(datos_izq) else ["", ""]
        der = datos_der[i] if i < len(datos_der) else ["", ""]
        filas_combinadas.append([izq[0], izq[1], der[0], der[1]])

    # Añadir medidor en una fila adicional si existe
    filas_combinadas.append([
        Paragraph("<b>Zona:</b>", style_label),
        Paragraph(datos_recibo['zona'], style_valor),
        Paragraph("<b>Medidor:</b>", style_label),
        Paragraph(datos_recibo['medidor'], style_valor)
    ])

    t_cliente = Table(filas_combinadas, colWidths=[1.0*inch, 2.5*inch, 1.0*inch, 2.5*inch])
    t_cliente.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(t_cliente)
    story.append(Spacer(1, 2))

    # Consumo (si no es deuda específica)
    if not datos_recibo.get('es_deuda_especifica', False):
        story.append(Paragraph("CONSUMO", style_seccion))
        lect_ant = datos_recibo.get('lectura_anterior', 0)
        lect_act = datos_recibo.get('lectura_actual', 0)
        consumo = datos_recibo.get('consumo', 0)

        data_consumo = [
            [
                Paragraph("<b>Lect. anterior:</b>", style_label),
                Paragraph(f"{lect_ant}" if lect_ant != "-" else "-", style_valor),
                Paragraph("<b>Lect. actual:</b>", style_label),
                Paragraph(f"{lect_act}" if lect_act != "-" else "-", style_valor),
                Paragraph("<b>Consumo (m³):</b>", style_label),
                Paragraph(f"{consumo}" if consumo != "-" else "-", style_valor),
            ],
        ]
        t_consumo = Table(data_consumo, colWidths=[1.0*inch, 1.3*inch, 1.0*inch, 1.3*inch, 1.3*inch, 1.1*inch])
        t_consumo.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 1),
            ('RIGHTPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(t_consumo)
        story.append(Spacer(1, 2))

    # Detalle de pago
    story.append(Paragraph("DETALLE DE PAGO", style_seccion))

    importe_consumo = datos_recibo.get('importe_consumo', 0)
    reconexion = datos_recibo.get('reconexion', 0)
    deuda = datos_recibo.get('deuda', 0)
    total = datos_recibo.get('total', 0)

    if datos_recibo.get('es_deuda_especifica', False):
        label_concepto = f"Pago Deuda - {datos_recibo['periodo']}"
    else:
        label_concepto = "Importe consumo:"

    data_pago = [
        [Paragraph(f"<b>{label_concepto}</b>", style_label), Paragraph(f"{importe_consumo:.2f} Bs", style_valor)],
    ]
    if reconexion > 0:
        data_pago.append([Paragraph("<b>Reconexión:</b>", style_label), Paragraph(f"{reconexion:.2f} Bs", style_valor)])
    if deuda > 0 and not datos_recibo.get('es_deuda_especifica', False):
        data_pago.append([Paragraph("<b>Pago pendiente:</b>", style_label), Paragraph(f"{deuda:.2f} Bs", style_valor)])
    data_pago.append([Paragraph("<b>TOTAL A PAGAR (Bs):</b>", style_total), Paragraph(f"{total:.2f} Bs", style_total)])

    t_pago = Table(data_pago, colWidths=[4.5*inch, 3.5*inch])
    t_pago.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-2), 3),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 6),
        ('TOPPADDING', (0,-1), (-1,-1), 4),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#1a5276')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#1a5276')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#eaf2f8')),
    ]))
    story.append(t_pago)
    story.append(Spacer(1, 3))

    # Son (letras)
    monto_en_letras = numero_a_letras(total)
    story.append(Paragraph(f"<b>Son:</b> {monto_en_letras}", style_son))
    story.append(Spacer(1, 2))

    # Efectivo y cambio
    efectivo = datos_recibo.get('efectivo', 0)
    cambio = datos_recibo.get('cambio', 0)
    if efectivo > 0:
        story.append(Paragraph(f"<b>Efectivo:</b> {efectivo:.2f} Bs | <b>Cambio:</b> {cambio:.2f} Bs", style_valor))
        story.append(Spacer(1, 2))

    # Firmas
    firma_data = [
        ["_________________________", "_________________________"],
        [Paragraph(f"<b>{datos_recibo['nombre']}</b><br/>USUARIO", style_firma),
         Paragraph(f"<b>{membrete}</b><br/>EPSA", style_firma)]
    ]
    t_firma = Table(firma_data, colWidths=[3.5*inch, 3.5*inch])
    t_firma.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 1),
    ]))
    story.append(t_firma)

    # Pie
    pie = config_epsa.direccion if (config_epsa and config_epsa.direccion) else ""
    if config_epsa and config_epsa.telefono:
        pie += f" | Tel: {config_epsa.telefono}"
    if pie:
        story.append(Spacer(1, 1))
        story.append(Paragraph(pie, ParagraphStyle('Pie', parent=styles['Normal'], fontSize=5, alignment=TA_CENTER, textColor=colors.HexColor('#7f8c8d'), leading=6)))

    story.append(Paragraph(
        "Comprobante oficial de pago. Conserve su recibo.",
        ParagraphStyle('Legal', parent=styles['Normal'], fontSize=5, alignment=TA_CENTER, textColor=colors.HexColor('#95a5a6'), leading=6)
    ))

    return story, membrete

class TwoReceiptsDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        # Márgenes mínimos para maximizar espacio
        margin = 22
        separation = 4
        page_width, page_height = letter
        frame_width = page_width - 2 * margin
        # Cada recibo ocupa la mitad de la hoja menos la separación
        frame_height = (page_height - 2 * margin - separation) / 2

        frame1 = Frame(
            margin, margin + frame_height + separation,
            frame_width, frame_height,
            id='frame1',
            showBoundary=0,
            topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )
        frame2 = Frame(
            margin, margin,
            frame_width, frame_height,
            id='frame2',
            showBoundary=0,
            topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )
        self.addPageTemplates([
            PageTemplate(id='TwoFrames', frames=[frame1, frame2])
        ])
        
def generar_recibo_pdf(usuario, datos_recibo, config_epsa=None):
    """
    Genera un PDF con dos recibos idénticos por hoja (cliente y copia).
    """
    output_dir = Path("recibos")
    output_dir.mkdir(exist_ok=True)

    nombre_archivo = f"recibo_{datos_recibo['codigo']}_{datos_recibo['fecha'].strftime('%Y%m%d')}_{datos_recibo['nro_recibo']}.pdf"
    ruta = output_dir / nombre_archivo

    doc = TwoReceiptsDoc(str(ruta), pagesize=letter, leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
    styles = getSampleStyleSheet()

    story_uno, _ = _crear_contenido_recibo(usuario, datos_recibo, config_epsa, styles)

    # Duplicar con FrameBreak
    story_total = story_uno + [FrameBreak()] + story_uno

    doc.build(story_total)
    return str(ruta)