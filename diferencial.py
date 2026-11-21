"""¿Será dengue? Orientación para distinguir dengue de enfermedades parecidas.

NO ES UN DIAGNÓSTICO. Los síntomas se parecen mucho entre sí; solo un examen lo
confirma. Los pesos son una regla simple basada en cómo se describen
clásicamente estas enfermedades (guías de la OPS/OMS). PENDIENTE: validarlos con
un médico antes de usarlo de verdad.

Idea de seguridad: mientras no se descarte dengue, se trata como dengue
(paracetamol; nada de ibuprofeno ni aspirina).
"""

ENFERMEDADES = {
    "dengue": "Dengue",
    "chikungunya": "Chikungunya",
    "zika": "Zika",
    "influenza": "Influenza o COVID-19",
    "malaria": "Malaria",
    "resfriado": "Gripe o resfriado común",
    "alergia": "Alergia",
}

# clave: (texto, {enfermedad: peso})
SINTOMAS = {
    "fiebre_alta": ("Fiebre alta que empezó de golpe", dict(dengue=3, chikungunya=3, zika=1, influenza=3, malaria=3, resfriado=-1, alergia=-3)),
    "dolor_ojos": ("Dolor detrás de los ojos", dict(dengue=3, zika=1)),
    "dolor_cabeza": ("Dolor de cabeza fuerte", dict(dengue=2, chikungunya=1, zika=1, influenza=2, malaria=2, resfriado=1)),
    "dolor_muscular": ("Dolor de músculos y huesos (\"quebrantahuesos\")", dict(dengue=2, chikungunya=2, zika=1, influenza=3, malaria=1, resfriado=1)),
    "articulaciones": ("Dolor muy fuerte en manos, pies o rodillas, con hinchazón", dict(dengue=1, chikungunya=4, zika=2)),
    "sarpullido": ("Sarpullido o manchas rojas en la piel", dict(dengue=1, chikungunya=2, zika=3)),
    "ojos_rojos": ("Ojos rojos sin pus", dict(chikungunya=1, zika=4, alergia=1)),
    "tos_mocos": ("Tos, mocos o nariz tapada", dict(dengue=-1, chikungunya=-1, zika=-1, influenza=3, resfriado=3, alergia=2)),
    "garganta": ("Dolor de garganta", dict(influenza=2, dengue=-1, resfriado=2, alergia=1)),
    "escalofrios": ("Escalofríos y sudor fuertes, con fiebre que va y viene cada 1 a 3 días", dict(dengue=1, influenza=1, malaria=4)),
    "vomitos": ("Náuseas o vómitos", dict(dengue=1, chikungunya=1, influenza=1, malaria=2)),
    "sangrado": ("Sangrado leve de encías o nariz, o moretones sin golpe", dict(dengue=3)),
    "cansancio": ("Cansancio extremo", dict(dengue=1, chikungunya=2, zika=1, influenza=2, malaria=2, resfriado=1)),
    "mejoro_fiebre": ("Ya me bajó la fiebre (días 3 a 6) pero me siento PEOR", dict(dengue=4)),
    "estornudos": ("Estornudos seguidos y picazón en la nariz, los ojos o la garganta", dict(alergia=4, resfriado=1)),
    "sin_fiebre": ("NO tengo fiebre", dict(dengue=-3, chikungunya=-3, malaria=-3, influenza=-2, alergia=3, resfriado=0)),
    "zancudos": ("Me picaron zancudos o hay casos de dengue en mi colonia", dict(dengue=2, chikungunya=2, zika=2, malaria=1)),
    "zona_malaria": ("Estuve en zona de costa, Petén, Alta Verapaz o Izabal en las últimas 3 semanas", dict(malaria=3, dengue=1)),
}

# Señales de alarma: si hay cualquiera, va al centro HOY, sea lo que sea.
ALARMA = {
    "dolor_abdominal": "Dolor fuerte de estómago",
    "vomitos_seguidos": "Vómitos que no paran",
    "sangrado_fuerte": "Sangrado fuerte (vómito, heces o menstruación con sangre)",
    "somnolencia": "Mucho sueño, confusión o convulsiones",
    "dificultad_respirar": "Le cuesta respirar",
    "no_orina": "Casi no orina o tiene la boca muy seca",
}

QUE_HACER = {
    "dengue": "Trátalo como dengue: paracetamol, mucho líquido y reposo. NO ibuprofeno ni aspirina. Pide hemograma y prueba de dengue (NS1 hasta el día 5, anticuerpos después). Usa el chequeo diario de la app.",
    "chikungunya": "Se parece mucho al dengue y puede coexistir con él. Mientras no se descarte dengue: solo paracetamol. El dolor de las articulaciones puede durar semanas. Pide la prueba en el centro de salud.",
    "zika": "Suele ser leve. Si estás embarazada o puedes estarlo, consulta HOY a tu médico. Mientras no se descarte dengue: solo paracetamol.",
    "influenza": "Puede ser influenza o COVID-19. Hazte la prueba, descansa y toma líquido. Si hay riesgo de dengue en tu zona, no tomes ibuprofeno ni aspirina hasta que un médico lo descarte.",
    "resfriado": "Parece un resfriado o gripe común: descansa, toma líquido y paracetamol si te molesta. Si la fiebre aparece o sube, o pasan más de 3 días con fiebre, vuelve a revisar tus síntomas aquí.",
    "alergia": "Parece una alergia: estornudos y picazón sin fiebre. Evita lo que te la provoca (polvo, polen, humo). Una farmacia o tu médico pueden recomendarte un antihistamínico. Si aparece fiebre, vuelve a revisar aquí.",
    "malaria": "La malaria necesita una prueba de sangre (gota gruesa) y tratamiento rápido. Ve al centro de salud HOY y di que estuviste en zona de malaria.",
}


def evaluar(marcados: list[str], alarmas: list[str], embarazada: bool = False) -> dict:
    """Devuelve ranking de enfermedades, qué hacer y si debe ir hoy."""
    puntos = {k: 0 for k in ENFERMEDADES}
    for s in marcados:
        for enf, peso in SINTOMAS[s][1].items():
            puntos[enf] += peso
    orden = sorted(puntos.items(), key=lambda kv: -kv[1])
    mejor = orden[0][1]
    ranking = []
    for enf, p in orden:
        if mejor <= 0 or len(marcados) < 2:
            nivel = "pocos datos"
        elif p >= mejor * 0.99:
            nivel = "más compatible"
        elif p >= mejor * 0.6:
            nivel = "también posible"
        else:
            nivel = "menos probable"
        ranking.append(dict(clave=enf, nombre=ENFERMEDADES[enf], puntos=p, nivel=nivel))
    return dict(
        ranking=ranking,
        pocos_datos=len(marcados) < 2 or mejor <= 0,
        ir_hoy=bool(alarmas) or "mejoro_fiebre" in marcados or "sangrado" in marcados
               or "zona_malaria" in marcados and "escalofrios" in marcados
               or embarazada and "sarpullido" in marcados,
        embarazada_riesgo=embarazada and ("sarpullido" in marcados or "ojos_rojos" in marcados),
    )
