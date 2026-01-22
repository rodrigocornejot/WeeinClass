from django.apps import apps
from django.conf import settings
from django.core.files.base import File
from django.utils import timezone
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
import os

def M(model_name: str):
    return apps.get_model("cursos", model_name)

# ✅ Ruta simple (coloca tu PDF aquí)
# WeeinClass/static/cursos/certificados/template_certificado.pdf
TEMPLATE_CERT_PATH = Path(settings.MEDIA_ROOT) / "certificados" / "template_certificado.pdf"

CERT_OUTPUT_DIR = Path(settings.MEDIA_ROOT) / "certificados"
CERT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generar_codigo_certificado():
    """
    Genera un código correlativo por día:
    CW-DDMMAAAA-01, CW-DDMMAAAA-02, ...
    """
    Certificado = M("Certificado")
    hoy = timezone.localdate()
    base = f"CW-{hoy.strftime('%d%m%Y')}-"
    correlativo = Certificado.objects.filter(codigo__startswith=base).count() + 1
    return f"{base}{correlativo:02d}"

def emitir_certificado_si_corresponde(matricula):
    """
    Versión compatible:
    - Si ya existe certificado (OneToOne related_name='certificado'), lo retorna.
    - Si no cumple pago + asistencia, retorna None.
    - Si cumple, crea Certificado (sin PDF) y lo retorna.
    """
    Certificado = M("Certificado")

    # Ya existe (OneToOne)
    try:
        return matricula.certificado
    except Exception:
        pass

    if not puede_generar_certificado(matricula):
        return None

    cert = Certificado.objects.create(
        matricula=matricula,
        codigo=generar_codigo_certificado(),
        fecha_emision=timezone.localdate()
    )
    return cert


def verificar_y_generar_certificado(matricula):
    Certificado = M("Certificado")

    # Solo si cumple (pago + asistencias completas)
    if not puede_generar_certificado(matricula):
        return None

    # Evitar duplicado
    cert = Certificado.objects.filter(matricula=matricula).first()
    if not cert:
        cert = Certificado.objects.create(
            matricula=matricula,
            codigo=generar_codigo_certificado(),
            fecha_emision=timezone.localdate()
        )

    # Si ya tiene archivo, no regenerar
    if getattr(cert, "archivo_pdf", None):
        if cert.archivo_pdf:
            return cert

    # Generar PDF y guardarlo en FileField
    out_path = generar_certificado_pdf(matricula)  # Path

    with open(out_path, "rb") as f:
        # ✅ nombre FIJO (sin random)
        filename = f"certificado_matricula_{matricula.id}.pdf"

        # ✅ si existe uno anterior, bórralo para que no cree _xxxxx
        if cert.archivo_pdf:
            cert.archivo_pdf.delete(save=False)

        cert.archivo_pdf.save(filename, File(f), save=True)

    return cert

def crear_asistencias_para_matricula(matricula):
    """
    Crea los registros base de AsistenciaUnidad para la matrícula,
    uno por cada UnidadCurso del curso, con completado=False.
    No duplica si ya existen.
    """
    UnidadCurso = M("UnidadCurso")
    AsistenciaUnidad = M("AsistenciaUnidad")

    unidades = UnidadCurso.objects.filter(curso=matricula.curso).order_by("numero")

    for unidad in unidades:
        AsistenciaUnidad.objects.get_or_create(
            matricula=matricula,
            unidad=unidad,
            defaults={"completado": False},
        )

def obtener_datos_dashboard(curso_id):
    """
    Si tu dashboard usa otra lógica real, puedes reemplazarla luego.
    Por ahora evita que reviente el import en views.py.
    """
    return {
        "curso": curso_id,
        "asistencias": 0,
        "notas_promedio": 0,
    }

def generar_fechas(inicio, modalidad):
    """
    Retorna una lista de fechas (str YYYY-MM-DD) según la modalidad.
    - Full Day  -> 3 fechas (1 por semana)
    - Extendida -> 6 fechas (cada 2 días)
    """

    if not inicio or not modalidad:
        return []

    modalidad = modalidad.strip().lower()
    fechas = []

    if modalidad == "full day":
        for i in range(3):
            fechas.append((inicio + timedelta(weeks=i)).strftime("%Y-%m-%d"))

    elif modalidad == "extendida":
        for i in range(6):
            fechas.append((inicio + timedelta(days=i * 2)).strftime("%Y-%m-%d"))

    return fechas

def matricula_pagada(matricula) -> bool:
    try:
        return Decimal(matricula.saldo_pendiente or 0) <= Decimal("0.00")
    except Exception:
        return False

def matricula_asistencia_completa(matricula) -> bool:
    UnidadCurso = M("UnidadCurso")
    AsistenciaUnidad = M("AsistenciaUnidad")

    total_modulos = UnidadCurso.objects.filter(curso=matricula.curso).count()
    if total_modulos == 0:
        return False

    completados = (
        AsistenciaUnidad.objects.filter(matricula=matricula, completado=True)
        .values_list("unidad_id", flat=True)
        .distinct()
        .count()
    )
    return completados >= total_modulos

def puede_generar_certificado(matricula) -> bool:
    return matricula_pagada(matricula) and matricula_asistencia_completa(matricula)

# =========================================================
# GENERADOR DE CERTIFICADO
# =========================================================

def generar_certificado_pdf(matricula):
    import fitz  # PyMuPDF
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import white, black
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph, Frame
    from reportlab.lib.styles import ParagraphStyle
    from io import BytesIO
    from pathlib import Path
    from django.utils import timezone

    Clase = M("Clase")

    # ✅ Validar plantilla
    if not TEMPLATE_CERT_PATH.exists():
        raise FileNotFoundError(
            f"No encontré la plantilla: {TEMPLATE_CERT_PATH}\n"
            f"✅ Debe estar en: {Path(TEMPLATE_CERT_PATH)}"
        )

    alumno_nombre = (matricula.alumno.nombre or "").strip()
    curso_nombre = (matricula.curso.nombre or "").strip()

    fecha_inicio = getattr(matricula, "fecha_inicio", None)
    ultima_clase = (
        Clase.objects.filter(curso=matricula.curso, matriculas=matricula)
        .order_by("-fecha")
        .first()
    )
    fecha_fin = ultima_clase.fecha if ultima_clase else None

    horas = getattr(matricula.curso, "horas", None) or 24
    modalidad = "PRESENCIAL"
    hoy = timezone.localdate()

    # 👇 usa tu correlativo real si ya lo guardas en Certificado.codigo
    # si no, deja esta línea:
    codigo = getattr(getattr(matricula, "certificado", None), "codigo", None) or f"CW-{hoy.strftime('%d%m%Y')}-{matricula.id:02d}"

    def fmt_fecha_es(d):
        if not d:
            return ""
        meses = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
        return f"{d.day:02d} de {meses[d.month-1]} del {d.year}"

    if fecha_inicio and fecha_fin:
        rango = f"Realizado del {fmt_fecha_es(fecha_inicio)} al {fmt_fecha_es(fecha_fin)}"
    elif fecha_inicio:
        rango = f"Realizado desde {fmt_fecha_es(fecha_inicio)}"
    else:
        rango = ""

    # ✅ Texto como tu ejemplo (una sola frase, con wrap automático)
    parrafo = (
        f"Por haber participado y aprobado satisfactoriamente el curso de "
        f"<b>{curso_nombre.upper()}.</b> "
        f"{rango}, haciendo un total de {horas} horas académicas en modalidad "
        f"<b>{modalidad}.</b>"
    )
    lugar = f"Lima, {fmt_fecha_es(hoy)}"
    linea_codigo = f"CERTIFICADO - {codigo}"

    # -----------------------------
    # Helpers de dibujo
    # -----------------------------
    def mask_box(c, bbox, page_h, pad=2):
        x0, y0, x1, y1 = bbox
        # convertir coordenadas PDF (y abajo) a ReportLab (y arriba)
        rl_y0 = page_h - y1
        rl_y1 = page_h - y0
        c.setFillColor(white)
        c.setStrokeColor(white)
        c.rect(x0 - pad, rl_y0 - pad, (x1 - x0) + pad * 2, (rl_y1 - rl_y0) + pad * 2, fill=1, stroke=0)

    def y_center(bbox, page_h):
        x0, y0, x1, y1 = bbox
        cy = (y0 + y1) / 2
        return page_h - cy

    def fit_text_size(c, text, font_name, max_size, max_width):
        size = max_size
        while size > 8:
            c.setFont(font_name, size)
            if c.stringWidth(text, font_name, size) <= max_width:
                return size
            size -= 1
        return 8

    def draw_center_fit(c, text, x0, x1, y, font_name="Helvetica-Bold", max_size=28):
        text = (text or "").strip()
        max_width = (x1 - x0)
        size = fit_text_size(c, text, font_name, max_size, max_width)
        c.setFont(font_name, size)
        c.setFillColor(black)
        c.drawCentredString((x0 + x1) / 2, y, text)

    # -----------------------------
    # Abrir plantilla y detectar bboxes
    # -----------------------------
    doc = fitz.open(str(TEMPLATE_CERT_PATH))
    page = doc[0]

    # Tamaño REAL del PDF plantilla (esto corrige el “chueco”)
    page_w = float(page.rect.width)
    page_h = float(page.rect.height)

    blocks = page.get_text("dict").get("blocks", [])

    def find_bbox_contains(txt):
        t = (txt or "").strip()
        for b in blocks:
            if b.get("type") != 0:
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if t and t in (s.get("text") or ""):
                        return s.get("bbox")
        return None

    # ✅ Busca textos del template (usa los que SÍ existen en tu PDF)
    bbox_name   = find_bbox_contains("Victor Marcelo") or (240, 220, 660, 260)
    bbox_course = find_bbox_contains("VARIADORES DE FRECUENCIA") or (145, 328, 520, 348)

    # En tu template, el párrafo suele contener “Realizado del”
    bbox_para   = find_bbox_contains("Realizado del") or (140, 340, 700, 390)

    bbox_lugar  = find_bbox_contains("Lima,") or (134, 409, 330, 427)
    bbox_codigo = find_bbox_contains("CERTIFICADO - CW") or find_bbox_contains("CERTIFICADO -") or (120, 520, 360, 545)

    # -----------------------------
    # Canvas + fondo (plantilla)
    # -----------------------------
    out_name = f"certificado_matricula_{matricula.id}.pdf"
    out_path = CERT_OUTPUT_DIR / out_name

    c = canvas.Canvas(str(out_path), pagesize=(page_w, page_h))

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    bg = ImageReader(BytesIO(pix.tobytes("png")))
    c.drawImage(bg, 0, 0, width=page_w, height=page_h)

    # -----------------------------
    # 1) Borrar SOLO lo variable (sin tocar la firma)
    # -----------------------------
    mask_box(c, bbox_name, page_h, pad=6)
    mask_box(c, bbox_course, page_h, pad=4)

    # ✅ para el párrafo, hacemos una caja limpia (no tapa firma porque queda arriba)
    # Ajusta solo si tu firma está más arriba (normalmente no)
    mask_box(c, bbox_para, page_h, pad=6)

    mask_box(c, bbox_lugar, page_h, pad=4)
    mask_box(c, bbox_codigo, page_h, pad=4)

    # -----------------------------
    # 2) Escribir prolijo (como tu ejemplo)
    # -----------------------------
    # Nombre (centrado)
    draw_center_fit(
        c,
        alumno_nombre,
        bbox_name[0], bbox_name[2],
        y_center(bbox_name, page_h) - 4,
        font_name="Helvetica-Bold",
        max_size=30
    )

    # Curso (centrado, un poco más pequeño)
    draw_center_fit(
        c,
        curso_nombre.upper(),
        bbox_course[0], bbox_course[2],
        y_center(bbox_course, page_h) - 3,
        font_name="Helvetica-Bold",
        max_size=14
    )

    # Párrafo con WRAP dentro de bbox_para (esto es lo que te faltaba)
    style = ParagraphStyle(
        name="cert",
        fontName="Helvetica",
        fontSize=11,
        leading=13,
        textColor=black,
    )

    # Frame usa coord ReportLab (y desde abajo)
    para_x0, para_y0, para_x1, para_y1 = bbox_para
    frame_x = para_x0
    frame_y = page_h - para_y1   # y inferior RL
    frame_w = (para_x1 - para_x0)
    frame_h = (para_y1 - para_y0)

    frame = Frame(frame_x, frame_y, frame_w, frame_h, leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
    frame.addFromList([Paragraph(parrafo, style)], c)

    # Lugar/fecha
    c.setFont("Helvetica", 11)
    c.setFillColor(black)
    c.drawString(bbox_lugar[0], y_center(bbox_lugar, page_h) - 4, lugar)

    # Código
    c.setFont("Helvetica", 11)
    c.setFillColor(black)
    c.drawString(bbox_codigo[0], y_center(bbox_codigo, page_h) - 4, linea_codigo)

    c.showPage()
    c.save()
    doc.close()

    return out_path


