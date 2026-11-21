"""Centros médicos: cercanía, saturación y asignación de médico.

IMPORTANTE: los centros, camas, tiempos de espera y médicos de CENTROS_DEMO son
INVENTADOS para el demo. En la vida real esos números los reportaría cada
centro (o el sistema de salud) y la app los leería. Para el pitch, díganlo:
"la saturación la reporta cada centro; aquí la simulamos".

Los centros REALES cercanos se pueden consultar en OpenStreetMap (buscar_osm),
pero OpenStreetMap NO trae ocupación ni médicos: se muestran solo como
referencia de ubicación.
"""
import math
import urllib.parse

# ----------------------------------------------------------------- umbrales
PCT_COLAPSADO = 0.90      # 90 % de camas ocupadas o más
PCT_OCUPADO = 0.70
ESPERA_COLAPSADO = 120    # minutos de espera en emergencia
ESPERA_OCUPADO = 60
VELOCIDAD_KMH = 20        # tráfico de la ciudad, para estimar el tiempo en carro


# --------------------------------------------------------------- datos demo
# nombre, tipo, lat, lon, camas, ocupadas, espera_min, emergencia, maternidad, pediatria
CENTROS_DEMO = [
    ("Centro de Salud Zona 18", "Centro de salud", 14.6600, -90.4830, 20, 19, 150, 1, 0, 0),
    ("Hospital General Zona 6", "Hospital", 14.6490, -90.5100, 120, 84, 60, 1, 1, 1),
    ("Hospital Nacional Zona 11", "Hospital", 14.6040, -90.5530, 300, 150, 35, 1, 1, 1),
    ("Hospital Nacional Zona 1", "Hospital", 14.6270, -90.5220, 250, 240, 180, 1, 1, 1),
    ("Centro de Salud Zona 6", "Centro de salud", 14.6560, -90.5030, 15, 6, 20, 0, 0, 0),
    ("Centro de Salud Zona 7", "Centro de salud", 14.6360, -90.5580, 12, 8, 30, 0, 0, 1),
    ("Centro de Salud Zona 12", "Centro de salud", 14.5890, -90.5380, 18, 10, 25, 0, 0, 0),
    ("Hospital de Villa Nueva", "Hospital", 14.5270, -90.5870, 90, 60, 45, 1, 1, 1),
    ("Centro de Atención Permanente Mixco", "Centro de atención permanente", 14.6340, -90.6040, 30, 25, 70, 1, 1, 0),
]

# centro (por nombre) -> médicos (nombre, especialidad). Nombres inventados.
MEDICOS_DEMO = {
    "Centro de Salud Zona 18": [("Dra. Mónica Reyes", "Medicina general"), ("Dr. Julio Cifuentes", "Medicina general")],
    "Hospital General Zona 6": [("Dra. Ana Lucía Barrios", "Infectología"), ("Dr. Esteban Ixcoy", "Medicina interna"),
                                ("Dra. Carla Monzón", "Ginecología"), ("Dr. Rodrigo Pop", "Pediatría")],
    "Hospital Nacional Zona 11": [("Dr. Marvin Estrada", "Infectología"), ("Dra. Silvia Chávez", "Medicina interna"),
                                  ("Dra. Patricia Lemus", "Ginecología"), ("Dr. Óscar Tzoc", "Pediatría")],
    "Hospital Nacional Zona 1": [("Dr. Hugo Mejía", "Medicina interna"), ("Dra. Beatriz Sandoval", "Ginecología"),
                                 ("Dr. Wilson Cac", "Pediatría")],
    "Centro de Salud Zona 6": [("Dr. Pablo Girón", "Medicina general"), ("Dra. Lucía Xicay", "Medicina general")],
    "Centro de Salud Zona 7": [("Dra. Karen Ajú", "Medicina general"), ("Dr. Iván Batz", "Pediatría")],
    "Centro de Salud Zona 12": [("Dr. Fernando Ochoa", "Medicina general"), ("Dra. Rosa Tuy", "Medicina general")],
    "Hospital de Villa Nueva": [("Dra. Gabriela Orantes", "Infectología"), ("Dr. Selvin Yat", "Medicina interna"),
                                ("Dra. Marta Quej", "Ginecología"), ("Dr. Alex Choc", "Pediatría")],
    "Centro de Atención Permanente Mixco": [("Dr. Byron Salazar", "Medicina general"), ("Dra. Heidy Cuc", "Ginecología")],
}

# Un hospital y un centro de salud (de ejemplo) en cada cabecera departamental del país.
from lugares import centros_del_pais
_c, _m = centros_del_pais()
CENTROS_DEMO += _c
MEDICOS_DEMO.update(_m)


# ------------------------------------------------------------------ cálculo
def distancia_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def minutos_en_carro(km: float) -> int:
    return max(3, round(km / VELOCIDAD_KMH * 60))


def estado(centro: dict, pacientes_graves_asignados: int = 0) -> dict:
    """Saturación del centro. Suma los pacientes en rojo que la app le asignó,
    porque van a necesitar cama: así la app detecta sola cuando se llena."""
    total = max(centro["camas_total"], 1)
    ocupadas = centro["camas_ocupadas"] + pacientes_graves_asignados
    pct = ocupadas / total
    espera = centro["espera_min"]
    if pct >= PCT_COLAPSADO or espera >= ESPERA_COLAPSADO:
        nivel, texto, emoji = "rojo", "Colapsado", "🔴"
    elif pct >= PCT_OCUPADO or espera >= ESPERA_OCUPADO:
        nivel, texto, emoji = "amarillo", "Muy ocupado", "🟡"
    else:
        nivel, texto, emoji = "verde", "Disponible", "🟢"
    return dict(nivel=nivel, texto=texto, emoji=emoji, pct=min(pct, 1.0),
                libres=max(total - ocupadas, 0), ocupadas=ocupadas, espera=espera)


def necesidades(paciente: dict, nivel_riesgo: str) -> dict:
    """Qué servicios necesita este paciente según su perfil."""
    edad = paciente.get("edad") or 30
    conds = paciente.get("condiciones", [])
    return dict(
        emergencia=nivel_riesgo == "rojo",
        maternidad="embarazo" in conds,
        pediatria=edad < 15,
    )


def cumple(centro: dict, nec: dict) -> bool:
    return ((not nec["emergencia"] or centro["emergencia"])
            and (not nec["maternidad"] or centro["maternidad"])
            and (not nec["pediatria"] or centro["pediatria"]))


def ordenar(centros: list[dict], paciente: dict, nivel_riesgo: str, graves_por_centro: dict) -> list[dict]:
    """Centros con distancia, estado y si sirven para este paciente. El primero
    es el recomendado: el más cercano que sirve y NO está colapsado."""
    nec = necesidades(paciente, nivel_riesgo)
    out = []
    for c in centros:
        km = distancia_km(paciente["lat"], paciente["lon"], c["lat"], c["lon"])
        e = estado(c, graves_por_centro.get(c["id"], 0))
        out.append(dict(c, km=km, minutos=minutos_en_carro(km), est=e, sirve=cumple(c, nec)))
    out.sort(key=lambda x: (not x["sirve"], x["est"]["nivel"] == "rojo", x["km"]))
    if out and out[0]["sirve"] and out[0]["est"]["nivel"] != "rojo":
        out[0]["recomendado"] = True
    for c in out:
        c.setdefault("recomendado", False)
    return out


def alternativa(centro_id: int, ordenados: list[dict]) -> dict | None:
    """Mejor centro distinto al actual que sirve y no está colapsado."""
    for c in ordenados:
        if c["id"] != centro_id and c["sirve"] and c["est"]["nivel"] != "rojo":
            return c
    return None


def elegir_medico(medicos: list[dict], paciente: dict, carga: dict) -> dict | None:
    """Médico del centro con la especialidad adecuada y menos pacientes."""
    if not medicos:
        return None
    conds, edad = paciente.get("condiciones", []), paciente.get("edad") or 30
    if "embarazo" in conds:
        pref = ("Ginecología",)
    elif edad < 15:
        pref = ("Pediatría",)
    else:
        pref = ("Infectología", "Medicina interna", "Medicina general")
    candidatos = [m for m in medicos if m["especialidad"] in pref] or medicos
    return min(candidatos, key=lambda m: carga.get(m["id"], 0))


# ---------------------------------------------------------------- enlaces
def enlace_ruta(lat_o, lon_o, lat_d, lon_d) -> str:
    return (f"https://www.google.com/maps/dir/?api=1&origin={lat_o},{lon_o}"
            f"&destination={lat_d},{lon_d}&travelmode=driving")


def enlace_whatsapp(telefono: str, mensaje: str) -> str:
    solo = "".join(ch for ch in telefono if ch.isdigit())
    return f"https://wa.me/502{solo}?text={urllib.parse.quote(mensaje)}"


# --------------------------------------------------- centros reales (OSM)
def buscar_osm(lat: float, lon: float, radio_m: int = 6000, limite: int = 12) -> list[dict]:
    """Hospitales y clínicas REALES cerca, de OpenStreetMap (gratis, sin llave).
    Solo se envían coordenadas de la zona, nunca datos del paciente.
    Devuelve [] si no hay internet. No incluye ocupación ni médicos."""
    try:
        import requests
        q = (f'[out:json][timeout:15];nwr["amenity"~"^(hospital|clinic)$"]["name"]'
             f"(around:{radio_m},{lat},{lon});out center 60;")
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q},
                          headers={"User-Agent": "DenGuaT-hackathon"}, timeout=20)
        r.raise_for_status()
        elementos = r.json().get("elements", [])
    except Exception:
        return []
    return _parsear_osm(elementos, lat, lon)[:limite]


def _parsear_osm(elementos: list[dict], lat: float, lon: float) -> list[dict]:
    vistos, out = set(), []
    for el in elementos:
        tags = el.get("tags", {})
        nombre = tags.get("name")
        la = el.get("lat") or el.get("center", {}).get("lat")
        lo = el.get("lon") or el.get("center", {}).get("lon")
        if not nombre or la is None or lo is None or nombre in vistos:
            continue
        vistos.add(nombre)
        km = distancia_km(lat, lon, la, lo)
        out.append(dict(nombre=nombre, tipo="Hospital" if tags.get("amenity") == "hospital" else "Clínica o centro de salud",
                        lat=la, lon=lo, km=km, minutos=minutos_en_carro(km),
                        telefono=tags.get("phone") or tags.get("contact:phone") or "",
                        emergencia=tags.get("emergency") == "yes"))
    return sorted(out, key=lambda x: x["km"])
