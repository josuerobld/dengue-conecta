"""Base de datos local (SQLite). Paciente y médico ven los mismos datos si
abren la app servida desde la misma laptop (el celular entra por la
"Network URL" que muestra Streamlit, en el mismo wifi)."""
import json
import sqlite3
from datetime import date
from pathlib import Path

RUTA = Path(__file__).parent / "dengue.db"


def con():
    c = sqlite3.connect(RUTA, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS pacientes(
        id INTEGER PRIMARY KEY, nombre TEXT, edad INT, telefono TEXT,
        zona TEXT, lat REAL, lon REAL, inicio_fiebre TEXT);
    CREATE TABLE IF NOT EXISTS chequeos(
        id INTEGER PRIMARY KEY, paciente_id INT, fecha TEXT, fiebre INT, signos TEXT);
    CREATE TABLE IF NOT EXISTS hemogramas(
        id INTEGER PRIMARY KEY, paciente_id INT, fecha TEXT,
        leucocitos REAL, plaquetas REAL, hematocrito REAL);
    CREATE TABLE IF NOT EXISTS centros(
        id INTEGER PRIMARY KEY, nombre TEXT, tipo TEXT, lat REAL, lon REAL,
        camas_total INT, camas_ocupadas INT, espera_min INT,
        emergencia INT, maternidad INT, pediatria INT, actualizado TEXT);
    CREATE TABLE IF NOT EXISTS medicos(
        id INTEGER PRIMARY KEY, centro_id INT, nombre TEXT, especialidad TEXT);
    """)
    cols = {r[1] for r in c.execute("PRAGMA table_info(pacientes)")}
    for col in ("condiciones", "medicamentos", "sexo"):
        if col not in cols:  # bases creadas con la versión anterior
            c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} TEXT DEFAULT ''")
    for col in ("centro_id", "medico_id"):
        if col not in cols:
            c.execute(f"ALTER TABLE pacientes ADD COLUMN {col} INTEGER")
    if "aviso" not in cols:
        c.execute("ALTER TABLE pacientes ADD COLUMN aviso TEXT DEFAULT ''")
    return c


def pacientes():
    out = []
    for r in con().execute("SELECT * FROM pacientes ORDER BY nombre"):
        p = dict(r)
        p["condiciones"] = json.loads(p.get("condiciones") or "[]")
        out.append(p)
    return out


def nuevo_paciente(nombre, edad, telefono, zona, lat, lon, inicio_fiebre: date,
                   condiciones: list[str] = (), medicamentos: str = "", sexo: str = "") -> int:
    c = con()
    cur = c.execute("INSERT INTO pacientes(nombre,edad,telefono,zona,lat,lon,inicio_fiebre,condiciones,medicamentos,sexo) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (nombre, edad, telefono, zona, lat, lon, inicio_fiebre.isoformat(),
                     json.dumps(list(condiciones)), medicamentos, sexo))
    c.commit()
    return cur.lastrowid


def actualizar_perfil(pid, condiciones: list[str], medicamentos: str):
    c = con()
    c.execute("UPDATE pacientes SET condiciones=?, medicamentos=? WHERE id=?",
              (json.dumps(list(condiciones)), medicamentos, pid))
    c.commit()


def guardar_chequeo(pid, fecha: date, fiebre: bool, signos: list[str]):
    c = con()
    c.execute("DELETE FROM chequeos WHERE paciente_id=? AND fecha=?", (pid, fecha.isoformat()))
    c.execute("INSERT INTO chequeos(paciente_id,fecha,fiebre,signos) VALUES(?,?,?,?)",
              (pid, fecha.isoformat(), int(fiebre), json.dumps(signos)))
    c.commit()


def guardar_hemograma(pid, fecha: date, leucocitos, plaquetas, hematocrito):
    c = con()
    c.execute("DELETE FROM hemogramas WHERE paciente_id=? AND fecha=?", (pid, fecha.isoformat()))
    c.execute("INSERT INTO hemogramas(paciente_id,fecha,leucocitos,plaquetas,hematocrito) VALUES(?,?,?,?,?)",
              (pid, fecha.isoformat(), leucocitos, plaquetas, hematocrito))
    c.commit()


def chequeos(pid):
    rows = con().execute("SELECT * FROM chequeos WHERE paciente_id=? ORDER BY fecha", (pid,))
    return [dict(r, fiebre=bool(r["fiebre"]), signos=json.loads(r["signos"])) for r in rows]


def hemogramas(pid):
    return [dict(r) for r in con().execute("SELECT * FROM hemogramas WHERE paciente_id=? ORDER BY fecha", (pid,))]


# ------------------------------------------------------------------ centros
def centros():
    return [dict(r) | {"emergencia": bool(r["emergencia"]), "maternidad": bool(r["maternidad"]),
                       "pediatria": bool(r["pediatria"])}
            for r in con().execute("SELECT * FROM centros ORDER BY nombre")]


def medicos(centro_id=None):
    if centro_id is None:
        rows = con().execute("SELECT * FROM medicos ORDER BY nombre")
    else:
        rows = con().execute("SELECT * FROM medicos WHERE centro_id=? ORDER BY nombre", (centro_id,))
    return [dict(r) for r in rows]


def cargar_centros(lista_centros, medicos_por_centro):
    """lista_centros: tuplas de centros.CENTROS_DEMO. Borra y vuelve a cargar."""
    from datetime import datetime
    c = con()
    c.executescript("DELETE FROM centros; DELETE FROM medicos;")
    for (nombre, tipo, lat, lon, camas, ocup, espera, emerg, mat, ped) in lista_centros:
        cur = c.execute("INSERT INTO centros(nombre,tipo,lat,lon,camas_total,camas_ocupadas,espera_min,"
                        "emergencia,maternidad,pediatria,actualizado) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (nombre, tipo, lat, lon, camas, ocup, espera, emerg, mat, ped,
                         datetime.now().isoformat(timespec="seconds")))
        for mn, esp in medicos_por_centro.get(nombre, []):
            c.execute("INSERT INTO medicos(centro_id,nombre,especialidad) VALUES(?,?,?)", (cur.lastrowid, mn, esp))
    c.commit()


def actualizar_centro(cid, camas_ocupadas, espera_min):
    from datetime import datetime
    c = con()
    c.execute("UPDATE centros SET camas_ocupadas=?, espera_min=?, actualizado=? WHERE id=?",
              (int(camas_ocupadas), int(espera_min), datetime.now().isoformat(timespec="seconds"), cid))
    c.commit()


def asignar(pid, centro_id, medico_id, aviso=""):
    """aviso: mensaje que el paciente verá en su pantalla hasta que lo marque como leído."""
    c = con()
    c.execute("UPDATE pacientes SET centro_id=?, medico_id=?, aviso=? WHERE id=?",
              (centro_id, medico_id, aviso, pid))
    c.commit()


def limpiar_aviso(pid):
    c = con()
    c.execute("UPDATE pacientes SET aviso='' WHERE id=?", (pid,))
    c.commit()


def borrar_todo():
    c = con()
    c.executescript("DELETE FROM pacientes; DELETE FROM chequeos; DELETE FROM hemogramas;")
    c.commit()
