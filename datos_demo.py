"""Carga pacientes FICTICIOS para el demo. Uso: python datos_demo.py

Pedro (zona 18) es el caso del pitch: día 3 bien, y el día 5 sus glóbulos
blancos caen y el hematocrito sube. El demo en vivo es subir el hemograma
del día 5 desde el celular (o usar el botón "Simular día 5" en la app).
"""
import random
from datetime import date, timedelta

import centros
import db

random.seed(3)
HOY = date.today()

# zona: (lat, lon) aproximados en Ciudad de Guatemala
ZONAS = {
    "Zona 18": (14.6560, -90.4870), "Zona 6": (14.6530, -90.5050),
    "Zona 7": (14.6380, -90.5560), "Zona 12": (14.5880, -90.5400),
    "Villa Nueva": (14.5260, -90.5870), "Mixco": (14.6330, -90.6060),
}
NOMBRES = ["Ana", "Brenda", "Carlos", "Diego", "Elena", "Fernando", "Gloria", "Héctor",
           "Irma", "José", "Karla", "Luis", "María", "Nery", "Olga", "Rosa", "Sergio"]


def jitter(lat, lon):
    return lat + random.uniform(-0.008, 0.008), lon + random.uniform(-0.008, 0.008)


COND_DEMO = {1: ["embarazo"], 5: ["hipertension"], 7: ["anticoagulante", "cardiaca"], 9: ["obesidad"]}


def cargar():
    db.borrar_todo()
    db.cargar_centros(centros.CENTROS_DEMO, centros.MEDICOS_DEMO)
    # --- Pedro: el caso del pitch (llega hasta el día 4; el día 5 se sube en vivo)
    lat, lon = jitter(*ZONAS["Zona 18"])
    inicio = HOY - timedelta(days=4)  # hoy es su día 5
    pid = db.nuevo_paciente("Pedro Xol", 34, "5555-0000", "Zona 18", lat, lon, inicio,
                            condiciones=["diabetes"], medicamentos="Metformina 850 mg", sexo="Hombre")
    for d, fiebre in [(1, True), (2, True), (3, True), (4, False)]:
        db.guardar_chequeo(pid, inicio + timedelta(days=d - 1), fiebre, [])
    db.guardar_hemograma(pid, inicio + timedelta(days=2), 5200, 165_000, 40)   # día 3

    # --- otros pacientes con distintos riesgos
    zonas_peso = ["Zona 18"] * 5 + ["Zona 6"] * 2 + ["Zona 7"] * 2 + ["Zona 12", "Villa Nueva", "Mixco"] * 2
    for i, nombre in enumerate(NOMBRES[:14]):
        zona = "Zona 18" if i in (0, 3, 6) else random.choice(zonas_peso)
        lat, lon = jitter(*ZONAS[zona])
        dias = 5 if i < 5 else random.randint(2, 7)
        inicio = HOY - timedelta(days=dias - 1)
        pid = db.nuevo_paciente(f"{nombre} {random.choice(['López','Pérez','Ajú','Coc','Ramírez','Tzul'])}",
                                27 if i == 1 else random.randint(5, 70), "5555-%04d" % random.randint(0, 9999), zona, lat, lon, inicio,
                                condiciones=COND_DEMO.get(i, []))
        grave = i < 2          # 2 urgentes
        moderado = 2 <= i < 5  # 3 para consultar hoy
        hto0 = random.uniform(36, 44)
        leu, pla, hto = random.uniform(4800, 7000), random.uniform(150_000, 250_000), hto0
        for d in range(1, dias + 1):
            f = inicio + timedelta(days=d - 1)
            signos = ["dolor_abdominal"] if grave and d == dias and i == 0 else []
            db.guardar_chequeo(pid, f, d < 4, signos)
            if d in (2, dias) and d > 1 or d == 1:
                if grave:
                    leu *= 0.7; pla *= 0.55; hto *= 1.12
                elif moderado:
                    leu *= 0.8; pla *= 0.95; hto *= 1.03
                else:
                    leu *= 0.93; pla *= 0.85; hto *= 1.02
                db.guardar_hemograma(pid, f, round(leu, -2), round(pla, -3), round(hto, 1))
    # --- los demás pacientes ya tienen centro y médico (Pedro NO: él lo elige en el demo)
    cs = db.centros()
    for p in db.pacientes():
        if p["nombre"] == "Pedro Xol":
            continue
        cercano = min(cs, key=lambda c: centros.distancia_km(p["lat"], p["lon"], c["lat"], c["lon"]))
        med = centros.elegir_medico(db.medicos(cercano["id"]), p, {})
        db.asignar(p["id"], cercano["id"], med["id"] if med else None)
    print("Datos de demo cargados.")


if __name__ == "__main__":
    cargar()
