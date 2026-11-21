"""Reglas de riesgo de dengue grave.

Basadas en el hallazgo de Madewell et al., "Machine learning for predicting
severe dengue in Puerto Rico", Infectious Diseases of Poverty (feb 2025),
DOI 10.1186/s40249-025-01273-0: las variables que más pesaron fueron
leucopenia (< 4,000/mm3), hemoconcentración (hematocrito que sube >= 20 %)
y estar entre el día 4 y 6 de la enfermedad. Los signos de alarma vienen de
la guía de dengue de la OMS/OPS.

Esto es un apoyo para el médico, no un diagnóstico.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

SIGNOS_ALARMA = {
    "dolor_abdominal": "Dolor fuerte de estómago",
    "vomitos": "Vómitos que no paran",
    "sangrado": "Sangrado de encías, nariz o en vómito/heces",
    "somnolencia": "Mucho sueño, irritable o confundido",
    "orina_poca": "Casi no orina",
    "frio_piel": "Manos y pies fríos o pegajosos",
}

LEUCOPENIA = 4000          # glóbulos blancos /mm3
PLAQUETAS_BAJAS = 100_000  # /mm3
HEMOCONCENTRACION = 0.20   # +20 % sobre el primer hematocrito


# Condiciones que la guía de dengue de la OMS/OPS considera de mayor riesgo
# (embarazo, edad extrema, obesidad, diabetes, hipertensión, enfermedad renal
# o cardíaca, etc.): estos pacientes necesitan seguimiento más cercano.
# Verifiquen la lista y los consejos con la guía de la OPS y un médico.
CONDICIONES = {
    "diabetes": ("Diabetes",
                 "Mide tu glucosa más seguido: la fiebre y comer poco la alteran. No dejes tu tratamiento "
                 "sin hablar con tu médico y pregúntale qué suero oral te conviene."),
    "hipertension": ("Presión alta (hipertensión)",
                     "No dejes tus medicinas de la presión. Avísale a tu médico si te sientes mareado o débil."),
    "embarazo": ("Embarazo",
                 "Estás en el grupo de mayor riesgo: consulta HOY en tu centro de salud aunque te sientas bien."),
    "renal": ("Enfermedad de los riñones",
              "Tu médico debe decirte cuánto líquido tomar: ni de más ni de menos."),
    "cardiaca": ("Enfermedad del corazón",
                 "Tu médico debe decirte cuánto líquido tomar. Avisa si te falta el aire."),
    "obesidad": ("Obesidad",
                 "Tienes más riesgo de complicarte: haz tu chequeo todos los días sin falta."),
    "anticoagulante": ("Tomo aspirina diaria o anticoagulantes",
                       "Aumentan el riesgo de sangrado. NO los dejes por tu cuenta: avísale HOY a tu médico."),
    "ulcera": ("Gastritis o úlcera en el estómago",
               "Tienes más riesgo de sangrado: avisa de inmediato si vomitas con sangre o haces heces negras."),
}


def condiciones_de_riesgo(condiciones: list[str], edad: int | None) -> list[str]:
    """Nombres legibles de las condiciones de riesgo, incluida la edad."""
    salida = [CONDICIONES[c][0] for c in condiciones if c in CONDICIONES]
    if edad is not None and edad < 1:
        salida.append("Bebé menor de 1 año")
    elif edad is not None and edad >= 65:
        salida.append("Adulto mayor (65+)")
    return salida


@dataclass
class Resultado:
    nivel: str                      # "verde" | "amarillo" | "rojo"
    puntaje: int
    razones: list[str] = field(default_factory=list)

    @property
    def emoji(self):
        return {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}[self.nivel]

    @property
    def consejo(self):
        return {
            "verde": "Sigue en casa: toma muchos líquidos, descansa y haz tu chequeo mañana.",
            "amarillo": "Consulta HOY en tu centro de salud. Sigue tomando líquidos.",
            "rojo": "Ve a EMERGENCIA AHORA. Tu médico ya fue avisado.",
        }[self.nivel]


# Reloj del demo: permite "avanzar días" para mostrar todo el flujo. Es del proceso
# (lo comparten paciente y médico, porque en el demo usan la misma app).
OFFSET_DIAS = 0


def hoy_actual() -> date:
    return date.today() + timedelta(days=OFFSET_DIAS)


# Qué le pasa a un paciente típico cada día de la enfermedad (para simular):
# día: (fiebre, signos, leucocitos, plaquetas, hematocrito)
SIMULACION = {
    1: (True, [], 6500, 190_000, 40.0), 2: (True, [], 5600, 170_000, 40.5),
    3: (True, [], 4700, 150_000, 41.5), 4: (True, [], 3900, 118_000, 44.0),
    5: (False, [], 3100, 88_000, 48.5), 6: (False, ["dolor_abdominal", "vomitos"], 2700, 62_000, 50.0),
}


def simulacion_del_dia(dia: int):
    return SIMULACION[min(max(dia, 1), 6)]


def dia_enfermedad(inicio_fiebre: date, hoy: date | None = None) -> int:
    hoy = hoy or hoy_actual()
    return (hoy - inicio_fiebre).days + 1


def evaluar(inicio_fiebre: date, chequeos: list[dict], hemogramas: list[dict],
            hoy: date | None = None, condiciones: list[str] = (), edad: int | None = None) -> Resultado:
    """chequeos: [{fecha, fiebre: bool, signos: [claves]}] ordenados por fecha.
    hemogramas: [{fecha, leucocitos, plaquetas, hematocrito}] ordenados por fecha."""
    dia = dia_enfermedad(inicio_fiebre, hoy)
    razones, puntos, rojo = [], 0, False
    def add(peso, texto):
        razones.append((peso, texto))

    if chequeos:
        ult = chequeos[-1]
        signos = ult.get("signos", [])
        if signos:
            rojo = True
            add(9, "Signos de alarma: " + ", ".join(SIGNOS_ALARMA[s] for s in signos))
        # la fase crítica suele empezar cuando BAJA la fiebre (defervescencia)
        if len(chequeos) >= 2 and chequeos[-2].get("fiebre") and not ult.get("fiebre") and 3 <= dia <= 7:
            puntos += 1
            add(2, f"Le bajó la fiebre en el día {dia}: empieza la fase crítica")

    if 4 <= dia <= 6:
        puntos += 1
        add(1, f"Día {dia} de la enfermedad (fase crítica, días 4 a 6)")

    if hemogramas:
        ult = hemogramas[-1]
        if ult.get("leucocitos") and ult["leucocitos"] < LEUCOPENIA:
            puntos += 2
            add(5, f"Glóbulos blancos bajos: {ult['leucocitos']:,.0f} (< {LEUCOPENIA:,})")
        if ult.get("plaquetas") and ult["plaquetas"] < PLAQUETAS_BAJAS:
            puntos += 1
            add(3, f"Plaquetas bajas: {ult['plaquetas']:,.0f}")
        base = next((h["hematocrito"] for h in hemogramas if h.get("hematocrito")), None)
        if base and ult.get("hematocrito"):
            cambio = (ult["hematocrito"] - base) / base
            if cambio >= HEMOCONCENTRACION:
                puntos += 3
                add(6, f"Hematocrito subió {cambio:.0%} (de {base:.0f} % a {ult['hematocrito']:.0f} %): la sangre se está concentrando")
        if len(hemogramas) >= 2:
            ant = hemogramas[-2]
            if ant.get("plaquetas") and ult.get("plaquetas") and ult["plaquetas"] < ant["plaquetas"] * 0.7:
                puntos += 1
                add(4, f"Plaquetas cayeron {1 - ult['plaquetas'] / ant['plaquetas']:.0%} desde el examen anterior")

    riesgos = condiciones_de_riesgo(list(condiciones), edad)
    if riesgos:
        puntos += 1
        add(3.5, "Paciente de riesgo: " + ", ".join(riesgos))

    if rojo or puntos >= 4:
        nivel = "rojo"
    elif puntos >= 2:
        nivel = "amarillo"
    else:
        nivel = "verde"
    if riesgos and nivel == "verde":
        nivel = "amarillo"  # la guía pide seguimiento cercano para pacientes de riesgo
    razones = [t for _, t in sorted(razones, key=lambda x: -x[0])] or ["Sin señales de riesgo por ahora"]
    return Resultado(nivel, puntos + (10 if rojo else 0), razones)
