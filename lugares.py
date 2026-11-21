"""Lugares de TODA Guatemala (22 departamentos) para el registro, y centros de
ejemplo en cada cabecera departamental.

Coordenadas aproximadas. Los centros, camas, esperas y médicos generados aquí son
INVENTADOS para el demo (en la vida real los reportaría cada centro).
"""
import zlib

# (departamento, lugar, lat, lon). La primera de cada departamento es la cabecera.
_L = [
    ("Guatemala", "Ciudad de Guatemala · Zona 1", 14.6270, -90.5220),
    ("Guatemala", "Ciudad de Guatemala · Zona 10", 14.5990, -90.5120),
    ("Guatemala", "Ciudad de Guatemala · Zona 21", 14.5700, -90.4900),
    ("Guatemala", "San Miguel Petapa", 14.5030, -90.5550),
    ("Guatemala", "Santa Catarina Pinula", 14.5670, -90.4900),
    ("Guatemala", "Chinautla", 14.7060, -90.4930),
    ("Sacatepéquez", "Antigua Guatemala", 14.5586, -90.7295),
    ("Sacatepéquez", "Ciudad Vieja", 14.5230, -90.7620),
    ("Chimaltenango", "Chimaltenango", 14.6630, -90.8190),
    ("Chimaltenango", "Tecpán Guatemala", 14.7640, -90.9930),
    ("Escuintla", "Escuintla", 14.3050, -90.7850),
    ("Escuintla", "Puerto San José", 13.9270, -90.8270),
    ("Escuintla", "Santa Lucía Cotzumalguapa", 14.3350, -91.0200),
    ("Santa Rosa", "Cuilapa", 14.2750, -90.2990),
    ("Santa Rosa", "Barberena", 14.3000, -90.4000),
    ("Sololá", "Sololá", 14.7720, -91.1830),
    ("Sololá", "Panajachel", 14.7410, -91.1590),
    ("Totonicapán", "Totonicapán", 14.9100, -91.3600),
    ("Quetzaltenango", "Quetzaltenango (Xela)", 14.8347, -91.5180),
    ("Quetzaltenango", "Coatepeque", 14.7000, -91.8650),
    ("Suchitepéquez", "Mazatenango", 14.5340, -91.5060),
    ("Suchitepéquez", "Cuyotenango", 14.5360, -91.5750),
    ("Retalhuleu", "Retalhuleu", 14.5390, -91.6770),
    ("San Marcos", "San Marcos", 14.9660, -91.7950),
    ("San Marcos", "Malacatán", 14.9110, -92.0580),
    ("Huehuetenango", "Huehuetenango", 15.3190, -91.4710),
    ("Huehuetenango", "La Democracia", 15.6900, -91.9300),
    ("Quiché", "Santa Cruz del Quiché", 15.0300, -91.1500),
    ("Quiché", "Chichicastenango", 14.9420, -91.1130),
    ("Quiché", "Ixcán", 15.9700, -90.7900),
    ("Baja Verapaz", "Salamá", 15.1010, -90.3150),
    ("Baja Verapaz", "Rabinal", 15.0830, -90.4850),
    ("Alta Verapaz", "Cobán", 15.4720, -90.3710),
    ("Alta Verapaz", "San Pedro Carchá", 15.4790, -90.3090),
    ("Petén", "Flores", 16.9300, -89.8930),
    ("Petén", "San Benito", 16.9180, -89.9080),
    ("Petén", "Poptún", 16.3300, -89.4200),
    ("Izabal", "Puerto Barrios", 15.7270, -88.5940),
    ("Izabal", "Morales", 15.4770, -88.8350),
    ("Izabal", "Livingston", 15.8280, -88.7510),
    ("Zacapa", "Zacapa", 14.9720, -89.5300),
    ("Chiquimula", "Chiquimula", 14.8000, -89.5440),
    ("Jalapa", "Jalapa", 14.6330, -89.9880),
    ("Jutiapa", "Jutiapa", 14.2920, -89.8960),
    ("Jutiapa", "Asunción Mita", 14.3330, -89.7080),
    ("El Progreso", "Guastatoya", 14.8530, -90.0680),
    ("Zacapa", "Estanzuela", 14.9760, -89.5600),
    ("Zacapa", "Río Hondo", 15.0330, -89.5900),
    ("Zacapa", "Teculután", 14.9930, -89.7000),
    ("Zacapa", "Gualán", 15.1270, -89.3600),
    ("Zacapa", "La Unión", 14.9560, -89.2840),
    ("Zacapa", "Usumatlán", 14.9500, -89.7500),
    ("Jutiapa", "El Progreso", 14.0600, -89.8600),
    ("Jutiapa", "Santa Catarina Mita", 14.4600, -89.7300),
    ("Jutiapa", "Moyuta", 14.0300, -90.1000),
    ("Jutiapa", "Quesada", 14.2800, -90.0400),
    ("Jutiapa", "Jalpatagua", 14.1400, -90.0200),
    ("Jutiapa", "Comapa", 14.1900, -89.9400),
    ("Chiquimula", "Esquipulas", 14.5640, -89.3510),
    ("Chiquimula", "Jocotán", 14.8160, -89.3970),
    ("Chiquimula", "Camotán", 14.8190, -89.3790),
    ("Jalapa", "Mataquescuintla", 14.5290, -90.1780),
    ("Jalapa", "San Pedro Pinula", 14.6670, -89.8480),
    ("El Progreso", "Sanarate", 14.7870, -90.2000),
    ("El Progreso", "Sansare", 14.7270, -90.1830),
    ("Santa Rosa", "Chiquimulilla", 14.0830, -90.3790),
    ("Santa Rosa", "Taxisco", 14.0700, -90.4670),
    ("Escuintla", "Masagua", 14.2000, -90.8200),
    ("Escuintla", "Tiquisate", 14.2830, -91.3600),
    ("Alta Verapaz", "Tactic", 15.3150, -90.3600),
    ("Izabal", "El Estor", 15.5330, -89.3300),
    ("Petén", "Sayaxché", 16.5250, -90.1850),
    ("Huehuetenango", "Jacaltenango", 15.6620, -91.7110),
    ("Quetzaltenango", "Salcajá", 14.8760, -91.4640),
    ("San Marcos", "Tecún Umán", 14.6670, -92.1450),
    ("Retalhuleu", "Champerico", 14.3000, -91.9140),
    ("Chimaltenango", "Patzún", 14.6830, -91.0170),
    ("Sacatepéquez", "Jocotenango", 14.5800, -90.7400),
    ("Guatemala", "Mixco", 14.6330, -90.6060),
    ("Guatemala", "Villa Nueva", 14.5260, -90.5870),
    ("Guatemala", "Zona 18", 14.6560, -90.4870),
    ("Guatemala", "Zona 6", 14.6530, -90.5050),
    ("Guatemala", "Zona 7", 14.6380, -90.5560),
    ("Guatemala", "Zona 12", 14.5880, -90.5400),
]

LUGARES = {f"{d} · {n}": (la, lo) for d, n, la, lo in _L}
POR_DEPARTAMENTO = {}
for _d, _n, _la, _lo in _L:
    POR_DEPARTAMENTO.setdefault(_d, {})[_n] = (_la, _lo)
DEPARTAMENTOS = sorted({d for d, *_ in _L})

_ESP = ["Medicina general", "Medicina interna", "Pediatría", "Ginecología", "Infectología"]
_APE = ["Aguilar", "Batz", "Cux", "Díaz", "Estrada", "García", "Hernández", "Itzep", "López", "Morales",
        "Pérez", "Quej", "Ramírez", "Sic", "Tzul", "Ucelo", "Vásquez", "Xol"]
_NOM = ["Ana", "Luis", "Marta", "Pedro", "Rosa", "Julio", "Carla", "Iván", "Elena", "Hugo"]


def _r(clave, n):
    return zlib.crc32(clave.encode()) % n


def centros_del_pais():
    """(centros, medicos_por_centro) de ejemplo: un hospital y un centro de salud
    en cada cabecera departamental, salvo Guatemala (ya tiene los suyos)."""
    centros, medicos = [], {}
    vistos = set()
    for d, n, la, lo in _L:
        if d in vistos or d == "Guatemala":
            continue
        vistos.add(d)
        ciudad = n.split(" (")[0]
        camas = 60 + _r(ciudad, 90)
        ocup = int(camas * (0.45 + _r(ciudad + "o", 40) / 100))
        h = f"Hospital Nacional de {ciudad}"
        centros.append((h, "Hospital", la + 0.004, lo + 0.004, camas, ocup, 25 + _r(ciudad + "e", 50), 1, 1, 1))
        cs = f"Centro de Salud de {ciudad}"
        cm = 10 + _r(ciudad + "c", 10)
        centros.append((cs, "Centro de salud", la - 0.004, lo - 0.004, cm, int(cm * 0.5), 20 + _r(ciudad + "s", 25), 0, 0, 0))
        for nombre in (h, cs):
            k = _r(nombre, 9)
            esp = _ESP if nombre == h else ["Medicina general", "Medicina general"]
            medicos[nombre] = [(f"{'Dra.' if (k + i) % 2 else 'Dr.'} {_NOM[(k + i) % 10]} {_APE[(k * 3 + i) % 18]}", e)
                               for i, e in enumerate(esp)]
    return centros, medicos
