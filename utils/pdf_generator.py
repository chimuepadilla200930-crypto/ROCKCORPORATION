"""
============================================================================
MODULO DE GENERACION DE REPORTES PDF EN ESPAÑOL - ROCK CORPORATION
============================================================================
Genera reportes PDF oficiales descargables de Productos y Usuarios.
============================================================================
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generar_pdf_reporte_productos(productos, tasa_cop_usd=3500.0):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#b60000'),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
        spaceAfter=15
    )

    cell_header_style = ParagraphStyle(
        'CellHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    cell_body_style = ParagraphStyle(
        'CellBody',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#222222')
    )

    cell_body_bold = ParagraphStyle(
        'CellBodyBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#111111')
    )

    story = []

    # Encabezado de Empresa
    story.append(Paragraph("ROCK CORPORATION", title_style))
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"REPORTE OFICIAL DE INVENTARIO Y PRODUCTOS | Generado: {fecha_actual} | TRM: $3.500 COP = 1 USD", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#b60000'), spaceAfter=15))

    # Tabla de Datos
    headers = [
        Paragraph("ID", cell_header_style),
        Paragraph("Nombre del Producto", cell_header_style),
        Paragraph("Descripción", cell_header_style),
        Paragraph("Stock", cell_header_style),
        Paragraph("Precio (COP)", cell_header_style),
        Paragraph("Estimado (USD)", cell_header_style)
    ]

    table_data = [headers]

    for p in productos:
        precio_cop = float(p.get('precio', 0))
        precio_usd = precio_cop / tasa_cop_usd
        
        row = [
            Paragraph(f"#{p.get('id')}", cell_body_bold),
            Paragraph(str(p.get('nombre', '')), cell_body_bold),
            Paragraph(str(p.get('descripcion', 'Sin descripción'))[:90] + ("..." if len(str(p.get('descripcion', ''))) > 90 else ""), cell_body_style),
            Paragraph(f"{p.get('stock', 0)} u.", cell_body_style),
            Paragraph(f"${precio_cop:,.0f}".replace(",", "."), cell_body_bold),
            Paragraph(f"${precio_usd:,.2f} USD", cell_body_style)
        ]
        table_data.append(row)

    # Anchos de columnas (total ~ 540 pt)
    col_widths = [35, 120, 195, 45, 75, 70]
    
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b60000')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8f8f9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e5')),
    ]))

    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"<b>Total de productos listados:</b> {len(productos)}", subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_reporte_producto_individual(producto, tasa_cop_usd=3500.0):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#b60000')
    )
    subtitle_style = ParagraphStyle(
        'SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#666666')
    )
    label_style = ParagraphStyle(
        'Label', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333')
    )
    val_style = ParagraphStyle(
        'Val', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#111111')
    )

    story = []
    story.append(Paragraph("ROCK CORPORATION", title_style))
    story.append(Paragraph(f"FICHA TECNICA Y DETALLE DE PRODUCTO #{producto.get('id')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#b60000'), spaceAfter=15))

    precio_cop = float(producto.get('precio', 0))
    precio_usd = precio_cop / tasa_cop_usd

    datos = [
        [Paragraph("ID Producto:", label_style), Paragraph(f"#{producto.get('id')}", val_style)],
        [Paragraph("Nombre:", label_style), Paragraph(str(producto.get('nombre')), val_style)],
        [Paragraph("Precio (COP):", label_style), Paragraph(f"${precio_cop:,.0f} COP".replace(",", "."), val_style)],
        [Paragraph("Estimado en Dólares:", label_style), Paragraph(f"${precio_usd:,.2f} USD (~ TRM $3.500)", val_style)],
        [Paragraph("Stock Disponible:", label_style), Paragraph(f"{producto.get('stock')} unidades", val_style)],
        [Paragraph("URL / Ruta Imagen:", label_style), Paragraph(str(producto.get('imagen_url', 'N/A')), val_style)],
        [Paragraph("Descripción Completa:", label_style), Paragraph(str(producto.get('descripcion', 'Sin descripción')), val_style)],
    ]

    t = Table(datos, colWidths=[150, 380])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f4f4f6')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
    ]))

    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_reporte_usuarios(usuarios):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, textColor=colors.HexColor('#b60000')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#555555')
    )
    cell_header = ParagraphStyle('CH', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)
    cell_body = ParagraphStyle('CB', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#222222'))
    cell_bold = ParagraphStyle('CBB', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#111111'))

    story = []
    story.append(Paragraph("ROCK CORPORATION", title_style))
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"REPORTE OFICIAL DE USUARIOS Y ROLES | Generado: {fecha_actual}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#b60000'), spaceAfter=15))

    headers = [
        Paragraph("ID", cell_header),
        Paragraph("Nombre Completo", cell_header),
        Paragraph("Correo Electrónico", cell_header),
        Paragraph("Rol", cell_header),
        Paragraph("Estado", cell_header)
    ]

    table_data = [headers]

    for u in usuarios:
        row = [
            Paragraph(f"#{u.get('id')}", cell_bold),
            Paragraph(str(u.get('nombre', u.get('nombre_completo', ''))), cell_bold),
            Paragraph(str(u.get('email', u.get('correo', ''))), cell_body),
            Paragraph(str(u.get('rol', 'Cliente')), cell_body),
            Paragraph(str(u.get('estado', 'Activo')), cell_body)
        ]
        table_data.append(row)

    col_widths = [40, 160, 200, 70, 70]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b60000')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8f8f9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e5')),
    ]))

    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"<b>Total de usuarios registrados:</b> {len(usuarios)}", subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
