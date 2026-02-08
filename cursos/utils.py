from django.apps import apps
from django.conf import settings
from django.core.files.base import File, ContentFile
from django.utils import timezone
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
import os
from io import BytesIO
from django.contrib.staticfiles import finders

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib.utils import ImageReader


def M(model_name: str):
    return apps.get_model("cursos", model_name)


CERT_OUTPUT_DIR = Path(settings.MEDIA_ROOT) / "certificados"
CERT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _buscar_fondo_certificado() -> str:
    """
    Busca el archivo de fondo usando staticfiles.
    Tu archivo debe estar en:  /static/certificados/certificado_base.jpeg
    """
    # prueba jpeg/jpg por si cambia la extensión
    for rel in ("certificados/certificado_base.jpeg", "certificados/certificado_base.jpg"):
        p = finders.find(rel)
        if p:
            return p
    return ""


def generar_codigo_certificado():
    """
    CW-DDMMAAAA-01, CW-DDMMAAAA-02, ...
    """
    Certificado = M("Certificado")
    hoy = timezone.localdate()
    base = f"CW-{hoy.strftime('%d%m%Y')}-"
    correlativo = Certificado.objects.filter(codigo__startswith=base).count() + 1
    return f"{base}{correlativo:02d}"


def emitir_certificado_si_corresponde(matricula):
    """
    - Si no cumple pago + asistencia => None
    - Si cumple => devuelve Certificado (creándolo si no existe)
    """
    Certificado = M("Certificado")

    if not puede_generar_certificado(matricula):
        return None

    cert = Certificado.objects.filter(matricula=matricula).first()
    if cert:
        return cert

    return Certificado.objects.create(
        matricula=matricula,
        codigo=generar_codigo_certificado(),
        fecha_emision=timezone.localdate()
    )


def verificar_y_generar_certificado(matricula, force_regen: bool = False):
    """
    Crea/obtiene Certificado y genera/actualiza el PDF en archivo_pdf.
    """
    Certificado = M("Certificado")

    cert = emitir_certificado_si_corresponde(matricula)
    if not cert:
        return None

    # Si ya tiene PDF y no forzamos regeneración, listo
    if cert.archivo_pdf and not force_regen:
        return cert

    # Generar bytes del PDF
    pdf_bytes = generar_pdf_certificado_bytes(
        matricula=matricula,
        codigo=cert.codigo,
        fecha_emision=cert.fecha_emision,
    )

    filename = f"certificado_matricula_{matricula.id}.pdf"

    # Si existe uno anterior, bórralo para evitar sufijos raros
    if cert.archivo_pdf:
        cert.archivo_pdf.delete(save=False)

    cert.archivo_pdf.save(filename, File(BytesIO(pdf_bytes)), save=True)
    return cert

# =========================================================
# ASISTENCIAS / VALIDACIONES
# =========================================================

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
# GENERADOR PDF (FONDO + TEXTO)
# =========================================================

def _find_cert_background() -> Path:
    candidates = [
        Path(settings.BASE_DIR) / "static" / "certificados" / "certificado_base.jpeg",
        Path(settings.BASE_DIR) / "static" / "certificados" / "certificado_base.jpg",
        Path(settings.BASE_DIR) / "cursos" / "static" / "certificados" / "certificado_base.jpeg",
        Path(settings.BASE_DIR) / "cursos" / "static" / "certificados" / "certificado_base.jpg",
        Path(getattr(settings, "MEDIA_ROOT", "")) / "certificados" / "certificado_base.jpeg",
        Path(getattr(settings, "MEDIA_ROOT", "")) / "certificados" / "certificado_base.jpg",
    ]

    for p in candidates:
        if str(p) and p.exists():
            return p

    rutas = "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(
        "No se encontró el fondo del certificado. Probé estas rutas:\n" + rutas
    )


def generar_pdf_certificado_bytes(matricula, codigo: str, fecha_emision):
    """
    Genera PDF: imagen base + textos (SIN duplicar el texto que ya viene en la imagen).
    Retorna bytes.
    """
    base_img_path = _buscar_fondo_certificado()
    if not base_img_path or not os.path.exists(base_img_path):
        raise FileNotFoundError(
            f"No se encontró el fondo del certificado en static/certificados/. "
            f"Verifica que exista: static/certificados/certificado_base.jpeg"
        )

    buffer = BytesIO()

    # A4 horizontal
    PAGE_SIZE = landscape((842, 595))
    c = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    W, H = PAGE_SIZE

    # Fondo
    c.drawImage(ImageReader(base_img_path), 0, 0, width=W, height=H, mask="auto")

    alumno = (matricula.alumno.nombre or "").strip()
    # ✅ Nombre completo del curso (no abreviado)
    try:
        curso = (matricula.curso.get_nombre_display() or "").strip()
    except Exception:
        curso = (matricula.curso.nombre or "").strip()
    fecha_txt = fecha_emision.strftime("%d de %B del %Y")  # ejemplo: 29 de enero del 2026
    # ReportLab no traduce meses a español por defecto; si quieres full español, dime y lo ajusto.
    # Por ahora usaremos formato corto para evitar raro:
    fecha_txt_corta = fecha_emision.strftime("%d/%m/%Y")

    # Fechas del curso (si tienes fecha_inicio en matrícula)
    fecha_inicio = getattr(matricula, "fecha_inicio", None) or getattr(matricula.curso, "fecha_inicio", None)
    if fecha_inicio:
        fi_txt = fecha_inicio.strftime("%d/%m/%Y")
    else:
        # fallback: usa fecha del curso
        fi_txt = matricula.curso.fecha.strftime("%d/%m/%Y") if getattr(matricula.curso, "fecha", None) else ""

    # Fecha fin: según cantidad de sesiones (unidades)
    UnidadCurso = M("UnidadCurso")
    sesiones = UnidadCurso.objects.filter(curso=matricula.curso).count() or 0

    # Si no hay unidades creadas, no inventamos: solo no mostramos rango bonito
    ff_txt = ""
    if fecha_inicio and sesiones:
        # asume 1 sesión por semana (cambia si tu lógica es distinta)
        ff = fecha_inicio + timedelta(weeks=max(sesiones - 1, 0))
        ff_txt = ff.strftime("%d/%m/%Y")

    # Horas académicas: duracion * sesiones (si duracion es “horas por sesión”)
    try:
        horas_por_sesion = int(getattr(matricula.curso, "duracion", 0) or 0)
    except Exception:
        horas_por_sesion = 0

    total_horas = horas_por_sesion * sesiones if (horas_por_sesion and sesiones) else horas_por_sesion

    # Modalidad: tu ejemplo dice PRESENCIAL
    modalidad = "PRESENCIAL"

    # =========================
    # TEXTOS (coordenadas)
    # =========================
    # OJO: NO dibujamos "CERTIFICADO OTORGADO A:" porque ya viene en la imagen base.

    # Nombre (script-like): usamos Times-Italic (se parece más al ejemplo)
    c.setFont("Times-Italic", 28)
    c.drawCentredString(W / 2, 330, alumno)

    # Línea (si tu base ya tiene línea, puedes borrar estas 2 líneas)
    # c.setLineWidth(1)
    # c.line(220, 315, W - 220, 315)

    # Párrafo como el ejemplo
    texto = f"Por haber participado y aprobado satisfactoriamente el curso de"
    c.setFont("Helvetica", 12)
    c.drawCentredString(W / 2, 270, texto)

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, 250, curso)

    # Rango de fechas + horas + modalidad (si hay datos)
    linea2 = []
    if fi_txt and ff_txt:
        linea2.append(f"Realizado del {fi_txt} al {ff_txt}")
    if total_horas:
        linea2.append(f"haciendo un total de {total_horas} horas académicas")
    linea2.append(f"en modalidad {modalidad}.")

    c.setFont("Helvetica", 11)
    c.drawCentredString(W / 2, 230, ". ".join(linea2))

    # Lugar y fecha (abajo-izq como tu ejemplo)
    c.setFont("Helvetica", 11)
    c.drawString(70, 120, f"Lima, {fecha_txt_corta}")

    # Código abajo-izq
    c.setFont("Helvetica", 10)
    c.drawString(70, 75, f"CERTIFICADO - {codigo}")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()