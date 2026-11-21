"""¿Me puedo tomar esto? Clasifica una medicina por su principio activo.

Fuente de las recomendaciones: guía de dengue de la OPS/OMS (paracetamol para
la fiebre; evitar AINEs y aspirina; antibióticos no sirven contra un virus).
DESCARGUEN la guía y citen la página exacta en el pitch.

La tabla de marcas es un punto de partida: verifíquenla en una farmacia de
Guatemala y agreguen las que vean (el nombre comercial puede variar).
"""
import re
import unicodedata

CATEGORIAS = {
    "aine": ("🔴", "NO lo tomes si puede ser dengue",
             "Es un antiinflamatorio: puede aumentar el riesgo de sangrado en dengue. "
             "Para la fiebre, la guía recomienda paracetamol."),
    "aspirina": ("🔴", "NO lo tomes si puede ser dengue",
                 "La aspirina (ácido acetilsalicílico) aumenta el riesgo de sangrado."),
    "antibiotico": ("🟠", "No sirve contra el dengue",
                    "El dengue es un virus; los antibióticos no lo curan. Solo con receta médica."),
    "corticoide": ("🟠", "Solo si te lo indicó un médico",
                   "No te lo tomes por tu cuenta."),
    "paracetamol": ("🟢", "Esto sí, con cuidado",
                    "Es lo que recomienda la guía para la fiebre y el dolor. "
                    "Respeta la dosis de la caja y no lo mezcles con otro producto que también tenga paracetamol."),
}

# principio activo o marca -> categoría  (todo en minúsculas y sin tildes)
PALABRAS = {
    # AINEs
    "ibuprofeno": "aine", "ibuprofen": "aine", "advil": "aine", "motrin": "aine",
    "diclofenaco": "aine", "diclofenac": "aine", "voltaren": "aine",
    "naproxeno": "aine", "naproxen": "aine", "flanax": "aine",
    "ketorolaco": "aine", "ketorolac": "aine",
    "meloxicam": "aine", "nimesulida": "aine", "piroxicam": "aine",
    "ketoprofeno": "aine", "celecoxib": "aine",
    # aspirina
    "acido acetilsalicilico": "aspirina", "aspirina": "aspirina", "aspirin": "aspirina",
    "alka-seltzer": "aspirina", "alka seltzer": "aspirina",
    # antibióticos
    "amoxicilina": "antibiotico", "azitromicina": "antibiotico", "ciprofloxacina": "antibiotico",
    "cefalexina": "antibiotico", "doxiciclina": "antibiotico", "trimetoprim": "antibiotico",
    "sulfametoxazol": "antibiotico", "clindamicina": "antibiotico", "claritromicina": "antibiotico",
    "levofloxacina": "antibiotico", "penicilina": "antibiotico",
    # corticoides
    "dexametasona": "corticoide", "prednisona": "corticoide", "betametasona": "corticoide",
    "hidrocortisona": "corticoide", "metilprednisolona": "corticoide",
    # paracetamol
    "paracetamol": "paracetamol", "acetaminofen": "paracetamol", "acetaminophen": "paracetamol",
    "panadol": "paracetamol", "tylenol": "paracetamol", "tempra": "paracetamol",
}

# Si hay varias, gana la más peligrosa
PRIORIDAD = ["aspirina", "aine", "corticoide", "antibiotico", "paracetamol"]


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def clasificar(texto: str) -> list[dict]:
    """Devuelve las medicinas encontradas en el texto (leído de la caja o escrito)."""
    t = _normalizar(texto)
    vistos = {}
    for palabra, cat in PALABRAS.items():
        if re.search(r"\b" + re.escape(palabra) + r"\b", t):
            vistos.setdefault(cat, []).append(palabra)
    salida = []
    for cat in PRIORIDAD:
        if cat in vistos:
            emoji, titulo, detalle = CATEGORIAS[cat]
            salida.append(dict(categoria=cat, encontrado=", ".join(vistos[cat]),
                               emoji=emoji, titulo=titulo, detalle=detalle))
    return salida


def leer_texto_de_imagen(img_bytes: bytes) -> str | None:
    """OCR opcional. Requiere `pip install pytesseract` y el programa Tesseract
    instalado (Windows: instalador de UB-Mannheim; Mac: brew install tesseract).
    Si no está, la app deja escribir el nombre a mano."""
    try:
        import io
        import os
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError:
        return None
    # En Windows el instalador lo deja aquí y no siempre lo agrega al PATH
    for ruta in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")):
        if os.path.exists(ruta):
            pytesseract.pytesseract.tesseract_cmd = ruta
            break
    img = ImageOps.grayscale(Image.open(io.BytesIO(img_bytes)))
    img = ImageOps.autocontrast(img)
    if max(img.size) < 1500:  # agrandar fotos chicas ayuda mucho al OCR
        f = 1500 / max(img.size)
        img = img.resize((int(img.width * f), int(img.height * f)))
    for idioma in ("spa+eng", "eng"):  # si no instalaron español, usa inglés
        try:
            return pytesseract.image_to_string(img, lang=idioma)
        except Exception:
            continue
    return None


def leer_hemograma(texto: str) -> dict:
    """Saca leucocitos, plaquetas y hematocrito de un texto de hemograma (OCR)."""
    t = _normalizar(texto).replace(",", "")
    def num(patron):
        m = re.search(patron + r"[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)", t)
        return float(m.group(1)) if m else None
    leu = num(r"(?:leucocitos|globulos blancos|wbc)")
    pla = num(r"(?:plaquetas|plt)")
    hto = num(r"(?:hematocrito|hct|hto)")
    # muchos laboratorios reportan en miles (5.2 = 5,200)
    if leu and leu < 100:
        leu *= 1000
    if pla and pla < 1000:
        pla *= 1000
    return {"leucocitos": leu, "plaquetas": pla, "hematocrito": hto}
