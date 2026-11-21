"""DengueConecta. Correr con:  streamlit run app.py
Para usarla en el celular: misma red wifi, abrir la "Network URL" que imprime Streamlit.
"""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

import centros
import db
import medicinas
import riesgo
from lugares import DEPARTAMENTOS, POR_DEPARTAMENTO

st.set_page_config(page_title="DengueConecta", page_icon="🦟", layout="wide", initial_sidebar_state="collapsed")

if not db.pacientes():
    import datos_demo
    datos_demo.cargar()
if not db.centros():  # base creada con una versión anterior
    db.cargar_centros(centros.CENTROS_DEMO, centros.MEDICOS_DEMO)

ss = st.session_state
ss.setdefault("vista", "inicio")


def ir(vista, **extra):
    ss.vista = vista
    ss.update(extra)
    st.rerun()


def evaluar_paciente(p, hoy=None):
    return riesgo.evaluar(date.fromisoformat(p["inicio_fiebre"]), db.chequeos(p["id"]), db.hemogramas(p["id"]), hoy,
                          condiciones=p.get("condiciones", []), edad=p.get("edad"))


def elegir_condiciones(actuales=(), key=""):
    st.write("**¿Tienes alguna de estas condiciones?** (marca todas las que apliquen)")
    cols = st.columns(2)
    return [k for i, (k, (nombre, _)) in enumerate(riesgo.CONDICIONES.items())
            if cols[i % 2].checkbox(nombre, value=k in actuales, key=f"{key}{k}")]


COLOR_ESTADO = {"rojo": [214, 69, 69, 230], "amarillo": [232, 163, 23, 230], "verde": [31, 157, 85, 230]}


def graves_por_centro():
    """Pacientes en rojo asignados a cada centro: van a necesitar cama."""
    out = {}
    for x in db.pacientes():
        if x.get("centro_id") and evaluar_paciente(x).nivel == "rojo":
            out[x["centro_id"]] = out.get(x["centro_id"], 0) + 1
    return out


def carga_medicos():
    out = {}
    for x in db.pacientes():
        if x.get("medico_id"):
            out[x["medico_id"]] = out.get(x["medico_id"], 0) + 1
    return out


def mapa_centros(orden, p):
    filas = [dict(nombre=c["nombre"], detalle=f'{c["est"]["emoji"]} {c["est"]["texto"]} · {c["km"]:.1f} km',
                  lat=c["lat"], lon=c["lon"], color=COLOR_ESTADO[c["est"]["nivel"]], radio=320) for c in orden]
    filas.append(dict(nombre="📍 Tú", detalle=p["zona"], lat=p["lat"], lon=p["lon"], color=[37, 99, 235, 255], radio=220))
    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(latitude=p["lat"], longitude=p["lon"], zoom=11.3),
        layers=[pdk.Layer("ScatterplotLayer", pd.DataFrame(filas), get_position="[lon, lat]",
                          get_fill_color="color", get_radius="radio", pickable=True)],
        tooltip={"text": "{nombre}\n{detalle}"}))


def asignar_centro(p, c, aviso=""):
    m = centros.elegir_medico(db.medicos(c["id"]), p, carga_medicos())
    db.asignar(p["id"], c["id"], m["id"] if m else None, aviso)
    return m


def ui_elegir_centro(p, r):
    """Lista de centros cercanos, con saturación, para que el paciente elija."""
    orden = centros.ordenar(db.centros(), p, r.nivel, graves_por_centro())
    nec = centros.necesidades(p, r.nivel)
    pide = [t for k, t in (("emergencia", "emergencia"), ("maternidad", "maternidad"), ("pediatria", "pediatría")) if nec[k]]
    if pide:
        st.info("Buscamos centros con: **" + ", ".join(pide) + "**, según tu situación.")
    st.caption("Centros, camas y esperas de ejemplo: en la vida real los reporta cada centro.")
    mapa_centros(orden, p)
    for c in orden[:6]:
        e = c["est"]
        with st.container(border=True):
            izq, der = st.columns([3, 1])
            etiqueta = "⭐ **Recomendado** · " if c["recomendado"] else ""
            izq.markdown(f"{etiqueta}**{c['nombre']}** · {c['tipo']}")
            izq.write(f"📍 {c['km']:.1f} km · ~{c['minutos']} min en carro   |   {e['emoji']} **{e['texto']}** · "
                      f"{e['libres']} camas libres · espera ~{e['espera']} min")
            if not c["sirve"]:
                izq.caption("⚠️ No tiene el servicio que necesitas.")
            elif e["nivel"] == "rojo":
                izq.caption("🔴 Está colapsado: mejor elige otro si puedes.")
            if der.button("Elegir" if e["nivel"] != "rojo" else "Elegir igual", key=f"el{c['id']}",
                          type="primary" if c["recomendado"] else "secondary", disabled=not c["sirve"],
                          width="stretch"):
                asignar_centro(p, c)
                st.rerun()


def ui_mi_centro(p, r, completo=True):
    """Tarjeta con el centro y médico asignados + aviso de saturación."""
    cs = {c["id"]: c for c in db.centros()}
    c = cs.get(p.get("centro_id"))
    if c is None:
        return None
    orden = centros.ordenar(list(cs.values()), p, r.nivel, graves_por_centro())
    actual = next(x for x in orden if x["id"] == c["id"])
    m = next((x for x in db.medicos(c["id"]) if x["id"] == p.get("medico_id")), None)
    e = actual["est"]
    if p.get("aviso"):
        st.warning("📩 **Mensaje de tu médico:** " + p["aviso"])
        if st.button("Entendido", key="aviso_ok"):
            db.limpiar_aviso(p["id"])
            st.rerun()
    nombre_m = f"{m['nombre']} ({m['especialidad']})" if m else "médico de guardia"
    st.markdown(f"🏥 **Tu centro:** {c['nombre']} · {actual['km']:.1f} km · ~{actual['minutos']} min  \n"
                f"👩‍⚕️ **Tu médico:** {nombre_m}. Ya recibió tus datos.")
    alt = centros.alternativa(c["id"], orden)
    if e["nivel"] == "rojo":
        st.error(f"🔴 **{c['nombre']} está colapsado** ({e['libres']} camas libres, espera ~{e['espera']} min).")
        if alt:
            st.success(f"✅ Te recomendamos **{alt['nombre']}**: a {alt['km']:.1f} km, "
                       f"{alt['est']['emoji']} {alt['est']['texto']}, espera ~{alt['est']['espera']} min.")
            if st.button(f"Cambiar a {alt['nombre']}", key="cambio_alt", type="primary"):
                asignar_centro(p, alt)
                st.rerun()
    elif e["nivel"] == "amarillo":
        st.warning(f"🟡 {c['nombre']} está muy ocupado: espera ~{e['espera']} min.")
    else:
        st.success(f"🟢 {c['nombre']} tiene lugar: {e['libres']} camas libres, espera ~{e['espera']} min.")
    destino = alt if (e["nivel"] == "rojo" and alt) else actual
    st.link_button("🚗 Cómo llegar (Google Maps)",
                   centros.enlace_ruta(p["lat"], p["lon"], destino["lat"], destino["lon"]))
    if r.nivel == "rojo":
        st.error(f"🚨 **Ve a emergencia AHORA a {destino['nombre']}** ({destino['km']:.1f} km, ~{destino['minutos']} min). "
                 "Tu médico ya fue avisado.")
    return orden


# ========================================================================= INICIO
if ss.vista == "inicio":
    st.markdown("<h1 style='text-align:center'>🦟 DengueConecta</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;font-size:1.2rem'>Si tienes dengue, tu médico te acompaña desde casa.<br>"
                "Te dice qué no tomar, cuándo ir al hospital y cuida a tu colonia.</p>", unsafe_allow_html=True)
    st.write("")
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        if st.button("📝 Es mi primera vez: registrarme", type="primary", width="stretch"):
            ir("registro")
        if st.button("🔑 Ya me registré: entrar con mi teléfono", width="stretch"):
            ir("entrar")
        st.divider()
        if st.button("🩺 Soy médico del centro de salud", width="stretch"):
            ir("medico")
        st.caption("Apoyo para el médico. No reemplaza el diagnóstico.")
        if st.button("🎬 Demo: entrar como Pedro", width="stretch"):
            pedro = next((x for x in db.pacientes() if x["nombre"] == "Pedro Xol"), None)
            if pedro:
                ir("paciente", pid=pedro["id"])
    st.stop()

# ======================================================================= REGISTRO
if ss.vista == "registro":
    if st.button("⬅️ Volver"):
        ir("inicio")
    st.title("📝 Registro")
    st.caption("Tus datos solo los ve tu médico del centro de salud.")
    d1, d2 = st.columns(2)
    depto = d1.selectbox("Departamento donde vives", DEPARTAMENTOS, index=DEPARTAMENTOS.index("Guatemala"), key="reg_depto")
    lugar = d2.selectbox("Municipio o zona (de ese departamento)", list(POR_DEPARTAMENTO[depto]), key=f"reg_lugar_{depto}")
    with st.form("reg"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre completo")
        tel = c2.text_input("Teléfono (para que tu médico te llame)")
        edad = c1.number_input("Edad", 0, 110, 30)
        sexo = c2.selectbox("Sexo", ["Mujer", "Hombre", "Prefiero no decir"])
        c1.text_input("Dónde vives", f"{lugar}, {depto}", disabled=True)
        inicio = c2.date_input("¿Qué día empezó la fiebre?", riesgo.hoy_actual() - timedelta(days=1))
        condiciones = elegir_condiciones(key="reg_")
        meds = st.text_input("¿Qué medicinas tomas siempre? (ej. metformina, losartán)")
        if st.form_submit_button("Registrarme", type="primary"):
            if not nombre:
                st.error("Escribe tu nombre.")
            elif "embarazo" in condiciones and sexo == "Hombre":
                st.error("Revisa: marcaste embarazo y sexo hombre.")
            else:
                zona = lugar if depto == "Guatemala" else f"{lugar}, {depto}"
                lat, lon = POR_DEPARTAMENTO[depto][lugar]
                pid = db.nuevo_paciente(nombre, edad, tel, zona, lat, lon, inicio, condiciones, meds, sexo)
                ir("paciente", pid=pid)
    st.stop()

# ========================================================================= ENTRAR
if ss.vista == "entrar":
    if st.button("⬅️ Volver"):
        ir("inicio")
    st.title("🔑 Entrar")
    tel = st.text_input("Escribe el teléfono con el que te registraste")
    if st.button("Entrar", type="primary") and tel:
        solo = lambda t: "".join(ch for ch in (t or "") if ch.isdigit())
        p = next((x for x in db.pacientes() if solo(x["telefono"]) == solo(tel)), None)
        if p:
            ir("paciente", pid=p["id"])
        st.error("No encontramos ese teléfono. ¿Es tu primera vez? Regístrate.")
    st.stop()

# ========================================================== BARRA LATERAL (dentro)
if st.sidebar.button("⬅️ Salir"):
    ir("inicio", pid=None)
st.sidebar.caption("Apoyo para el médico. No reemplaza el diagnóstico.")
with st.sidebar.expander("⏩ Simulador de días (demo)", expanded=riesgo.OFFSET_DIAS > 0):
    st.write(f"Hoy simulado: **{riesgo.hoy_actual().strftime('%d/%m/%Y')}**"
             + (f" (+{riesgo.OFFSET_DIAS} días)" if riesgo.OFFSET_DIAS else ""))
    if st.button("+1 día", key="sb_mas"):
        riesgo.OFFSET_DIAS += 1
        st.rerun()
    if st.button("↩️ Volver a hoy", key="sb_cero"):
        riesgo.OFFSET_DIAS = 0
        st.rerun()
rol = "👤 Paciente" if ss.vista == "paciente" else "🩺 Médico"

# ======================================================================= PACIENTE
if rol == "👤 Paciente":
    p = next((x for x in db.pacientes() if x["id"] == ss.get("pid")), None)
    if p is None:
        ir("inicio")
    dia = riesgo.dia_enfermedad(date.fromisoformat(p["inicio_fiebre"]))
    r = evaluar_paciente(p)
    st.title(f"Hola, {p['nombre'].split()[0]}")
    if not any(c["id"] == p.get("centro_id") for c in db.centros()):
        st.markdown("### Último paso: elige a qué centro de salud ir")
        st.write("Te mostramos los más cercanos, cuáles están llenos y cuáles tienen lugar. "
                 "Cuando elijas, **se te asigna un médico** que recibe tus datos.")
        ui_elegir_centro(p, r)
        st.stop()
    st.markdown(f"### Día **{dia}** de tu dengue  {r.emoji}")
    if 4 <= dia <= 6:
        st.warning("Estás en los días más delicados (4 a 6). Aunque te sientas mejor, haz tu chequeo hoy.")
    {"verde": st.success, "amarillo": st.warning, "rojo": st.error}[r.nivel](r.consejo)
    riesgos = riesgo.condiciones_de_riesgo(p.get("condiciones", []), p.get("edad"))
    if riesgos:
        st.info("🩺 **Eres paciente de riesgo** (" + ", ".join(riesgos) + "). Tu médico te sigue más de cerca. "
                "Mira tus cuidados en la pestaña **❤️ Mi salud**.")

    ui_mi_centro(p, r)
    t1, t2, t3, tc, t4, t5 = st.tabs(["✅ Chequeo de hoy", "🧪 Mi hemograma", "💊 ¿Me lo tomo?",
                                      "🏥 Mi centro", "❤️ Mi salud", "🦟 No contagies"])

    with t1:
        with st.form("chequeo"):
            fiebre = st.radio("¿Tienes fiebre hoy?", ["Sí", "No"], horizontal=True) == "Sí"
            st.write("¿Tienes alguno de estos? (marca todos los que apliquen)")
            signos = [k for k, v in riesgo.SIGNOS_ALARMA.items() if st.checkbox(v, key=k)]
            if st.form_submit_button("Enviar a mi médico", type="primary"):
                db.guardar_chequeo(p["id"], riesgo.hoy_actual(), fiebre, signos)
                st.rerun()

    with t2:
        st.write("Toma una foto de tu resultado de laboratorio. Tu médico lo verá sin que tengas que ir a consulta.")
        foto = st.file_uploader("📷 Foto del hemograma (en el celular abre la cámara)", type=["jpg", "jpeg", "png"])
        leido = {}
        if foto:
            st.image(foto, width=320)
            texto = medicinas.leer_texto_de_imagen(foto.getvalue())
            leido = medicinas.leer_hemograma(texto) if texto else {}
            if texto is None:
                st.warning("📷 Foto recibida, pero el lector de texto (Tesseract) no está instalado. "
                           "Escribe los números del papel aquí abajo.")
            elif any(leido.values()):
                st.success("Leí estos números de tu foto. Revisa que estén bien y envía:")
            else:
                st.warning("No pude leer los números en la foto. Escríbelos aquí abajo:")
        with st.form("hemo"):
            c1, c2, c3 = st.columns(3)
            leu = c1.number_input("Glóbulos blancos (leucocitos)", 0.0, 50000.0, leido.get("leucocitos") or 0.0, step=100.0)
            pla = c2.number_input("Plaquetas", 0.0, 900000.0, leido.get("plaquetas") or 0.0, step=1000.0)
            hto = c3.number_input("Hematocrito (%)", 0.0, 70.0, leido.get("hematocrito") or 0.0, step=0.5)
            if st.form_submit_button("Enviar a mi médico", type="primary") and leu and pla and hto:
                db.guardar_hemograma(p["id"], riesgo.hoy_actual(), leu, pla, hto)
                st.rerun()
        st.divider()
        st.caption("🎬 Demo: simula lo que le pasa a un paciente con dengue en cada día.")
        s1, s2 = st.columns(2)
        if s1.button(f"🎬 Simular mi chequeo y hemograma del día {dia}", key="sim_hoy"):
            fi, sg, le, pl, ht = riesgo.simulacion_del_dia(dia)
            db.guardar_chequeo(p["id"], riesgo.hoy_actual(), fi, sg)
            db.guardar_hemograma(p["id"], riesgo.hoy_actual(), le, pl, ht)
            st.rerun()
        if s2.button("⏩ Pasar al día siguiente y simular", key="sim_sig"):
            riesgo.OFFSET_DIAS += 1
            fi, sg, le, pl, ht = riesgo.simulacion_del_dia(dia + 1)
            db.guardar_chequeo(p["id"], riesgo.hoy_actual(), fi, sg)
            db.guardar_hemograma(p["id"], riesgo.hoy_actual(), le, pl, ht)
            st.rerun()

    with t3:
        st.write("Antes de tomarte algo, revisa si es seguro con dengue.")
        foto_m = st.file_uploader("📷 Foto de la caja", type=["jpg", "jpeg", "png"], key="med")
        texto = ""
        if foto_m:
            st.image(foto_m, width=320)
            texto = medicinas.leer_texto_de_imagen(foto_m.getvalue())
            if texto is None:
                st.warning("📷 Foto recibida, pero el lector de texto (Tesseract) no está instalado. "
                           "Escribe el nombre de la medicina aquí abajo.")
                texto = ""
            elif not medicinas.clasificar(texto):
                st.warning("No reconocí la medicina en la foto. Escribe el nombre aquí abajo.")
        escrito = st.text_input("…o escribe el nombre de la medicina")
        consulta = " ".join([texto, escrito]).strip()
        if consulta:
            res = medicinas.clasificar(consulta)
            if not res:
                st.info("No la reconozco. Pregúntale a tu médico o farmacéutico antes de tomarla.")
            for m in res:
                box = st.error if m["emoji"] == "🔴" else st.warning if m["emoji"] == "🟠" else st.success
                box(f"{m['emoji']} **{m['titulo']}** ({m['encontrado']}). {m['detalle']}")

    with tc:
        st.subheader("Centros cercanos y su estado")
        ui_elegir_centro(p, r)
        with st.expander("🗺️ Otros centros REALES cerca de ti (OpenStreetMap)"):
            st.caption("Solo ubicación: no tenemos su ocupación ni sus médicos. "
                       "Se envía a OpenStreetMap únicamente la ubicación de tu zona, nunca tus datos.")
            if st.button("Buscar centros reales", key="osm_btn"):
                ss["osm"] = centros.buscar_osm(p["lat"], p["lon"])
                ss["osm_vacio"] = not ss["osm"]
            if ss.get("osm_vacio"):
                st.info("No pude consultar OpenStreetMap (¿sin internet?).")
            for x in ss.get("osm", []):
                cols = st.columns([4, 1])
                cols[0].write(f"**{x['nombre']}** · {x['tipo']} · {x['km']:.1f} km"
                              + (f" · 📞 {x['telefono']}" if x["telefono"] else ""))
                cols[1].link_button("🚗 Ir", centros.enlace_ruta(p["lat"], p["lon"], x["lat"], x["lon"]))

    with t4:
        st.subheader("Tus cuidados con dengue")
        if not p.get("condiciones") and not riesgos:
            st.success("No registraste condiciones de riesgo. Sigue los cuidados generales: líquidos, reposo y chequeo diario.")
        for c in p.get("condiciones", []):
            if c in riesgo.CONDICIONES:
                nombre_c, consejo = riesgo.CONDICIONES[c]
                st.warning(f"**{nombre_c}:** {consejo}")
        if p.get("edad") is not None and (p["edad"] < 1 or p["edad"] >= 65):
            st.warning("**Edad:** los bebés y adultos mayores se complican más. Consulta hoy y no esperes signos de alarma.")
        if p.get("medicamentos"):
            st.write(f"💊 **Medicinas que tomas siempre:** {p['medicamentos']}")
            for m in medicinas.clasificar(p["medicamentos"]):
                if m["categoria"] in ("aine", "aspirina"):
                    st.error(f"{m['emoji']} Tomas {m['encontrado']}: aumenta el riesgo de sangrado con dengue. "
                             "**No la dejes por tu cuenta: avísale HOY a tu médico.**")
        with st.expander("✏️ Actualizar mis condiciones y medicinas"):
            with st.form("perfil"):
                nuevas = elegir_condiciones(p.get("condiciones", []), key="perf_")
                meds = st.text_input("Medicinas que tomas siempre", value=p.get("medicamentos") or "")
                if st.form_submit_button("Guardar"):
                    db.actualizar_perfil(p["id"], nuevas, meds)
                    st.rerun()

    with t5:
        st.markdown("""
**Mientras tengas fiebre, un mosquito que te pique se infecta y puede contagiar a tu familia.**

- 🛏️ Duerme y descansa **con mosquitero**, también de día.
- 🧴 Usa **repelente** y ropa de manga larga.
- 🪣 Revisa tu casa hoy: **voltea cubetas**, **tapa la pila**, cambia el agua de floreros, guarda llantas bajo techo.
- 👨‍👩‍👧 Si alguien más en casa tiene fiebre, regístralo también.
""")

# ========================================================================= MÉDICO
else:
    st.title("🩺 Panel del médico")
    cs = db.centros()
    meds = db.medicos()
    cs_por_id = {c["id"]: c for c in cs}
    med_por_id = {m["id"]: m for m in meds}
    graves = graves_por_centro()
    estados = {c["id"]: centros.estado(c, graves.get(c["id"], 0)) for c in cs}

    opciones = ["Todos los centros"] + [f"{m['nombre']} · {cs_por_id[m['centro_id']]['nombre']}" for m in meds]
    ver = st.selectbox("Ver como", opciones, help="Elige tu nombre para ver solo a tus pacientes.")
    todos = db.pacientes()
    if ver == "Todos los centros":
        ps = todos
    else:
        yo = meds[opciones.index(ver) - 1]
        ps = [x for x in todos if x.get("medico_id") == yo["id"]]
        st.caption(f"Mostrando a los pacientes de {yo['nombre']} en {cs_por_id[yo['centro_id']]['nombre']}.")

    # ---- alertas de saturación: la app las detecta sola
    colapsados = [c for c in cs if estados[c["id"]]["nivel"] == "rojo"
                  and any(x.get("centro_id") == c["id"] for x in ps)]
    for c in colapsados:
        e = estados[c["id"]]
        afectados = [x for x in ps if x.get("centro_id") == c["id"]]
        st.error(f"🔴 **{c['nombre']} está COLAPSADO** · {e['libres']} camas libres · espera ~{e['espera']} min · "
                 f"{len(afectados)} pacientes asignados ahí.")
        with st.expander(f"Derivar a los {len(afectados)} pacientes de {c['nombre']}"):
            plan = []
            for x in afectados:
                rx = evaluar_paciente(x)
                alt = centros.alternativa(c["id"], centros.ordenar(cs, x, rx.nivel, graves))
                plan.append((x, rx, alt))
                if alt:
                    msg = (f"Hola {x['nombre'].split()[0]}, tu centro ({c['nombre']}) está saturado. "
                           f"Te recomendamos ir a {alt['nombre']} ({alt['km']:.1f} km, espera ~{alt['est']['espera']} min). "
                           "DengueConecta")
                    f1, f2 = st.columns([4, 1])
                    f1.write(f"{rx.emoji} **{x['nombre']}** → {alt['nombre']} ({alt['km']:.1f} km)")
                    f2.link_button("📲 WhatsApp", centros.enlace_whatsapp(x["telefono"], msg))
                else:
                    st.write(f"{rx.emoji} **{x['nombre']}**: no hay otro centro disponible que le sirva.")
            if st.button(f"🔁 Derivar a todos y avisarles", key=f"der{c['id']}", type="primary"):
                for x, rx, alt in plan:
                    if alt:
                        asignar_centro(x, alt, f"Tu centro anterior ({c['nombre']}) se saturó. "
                                               f"Ahora te atiende {alt['nombre']}. Ve ahí si necesitas atención.")
                st.rerun()

    if not ps:
        st.info("Todavía no tienes pacientes asignados.")
    else:
        filas = []
        for p in ps:
            r = evaluar_paciente(p)
            hs = db.hemogramas(p["id"])
            cen = cs_por_id.get(p.get("centro_id"))
            med = med_por_id.get(p.get("medico_id"))
            filas.append(dict(id=p["id"], Riesgo=r.emoji, Paciente=p["nombre"], Edad=p["edad"], Zona=p["zona"],
                              Condiciones=", ".join(riesgo.condiciones_de_riesgo(p.get("condiciones", []), p["edad"])) or "—",
                              Día=riesgo.dia_enfermedad(date.fromisoformat(p["inicio_fiebre"])),
                              Centro=cen["nombre"] if cen else "Sin elegir", Médico=med["nombre"] if med else "—",
                              Motivo=r.razones[0], Teléfono=p["telefono"],
                              Leucocitos=hs[-1]["leucocitos"] if hs else None, _p=r.puntaje, _n=r.nivel,
                              lat=p["lat"], lon=p["lon"]))
        df = pd.DataFrame(filas).sort_values("_p", ascending=False)

        c = st.columns(4)
        c[0].metric("Pacientes en seguimiento", len(df))
        c[1].metric("🔴 Urgentes", int((df._n == "rojo").sum()))
        c[2].metric("🟡 Consultar hoy", int((df._n == "amarillo").sum()))
        c[3].metric("Pacientes de riesgo", int((df.Condiciones != "—").sum()))

        st.subheader("1. ¿A quién atiendo primero?")
        st.dataframe(df[["Riesgo", "Paciente", "Edad", "Condiciones", "Centro", "Médico", "Zona", "Día",
                         "Leucocitos", "Motivo", "Teléfono"]], hide_index=True, width="stretch")

        st.subheader("2. Evolución del paciente")
        sel = st.selectbox("Paciente", df.Paciente.tolist())
        p = next(x for x in ps if x["nombre"] == sel)
        r = evaluar_paciente(p)
        a, b = st.columns([2, 1])
        with b:
            st.markdown(f"### {r.emoji} {sel}")
            if p.get("medicamentos"):
                st.caption(f"Toma siempre: {p['medicamentos']}")
            for razon in r.razones:
                st.write("• " + razon)
            st.link_button("📲 Escribir por WhatsApp", f"https://wa.me/502{p['telefono'].replace('-', '')}")
        hs = pd.DataFrame(db.hemogramas(p["id"]))
        with a:
            if hs.empty:
                st.info("Todavía no ha subido hemogramas.")
            else:
                inicio = date.fromisoformat(p["inicio_fiebre"])
                hs["día"] = [riesgo.dia_enfermedad(inicio, date.fromisoformat(f)) for f in hs.fecha]
                graf = [("leucocitos", "Glóbulos blancos", riesgo.LEUCOPENIA, "debajo"),
                        ("plaquetas", "Plaquetas", riesgo.PLAQUETAS_BAJAS, "debajo"),
                        ("hematocrito", "Hematocrito (%)", hs.hematocrito.iloc[0] * (1 + riesgo.HEMOCONCENTRACION), "encima")]
                for col, (campo, titulo, limite, lado) in zip(st.columns(3), graf):
                    fig = go.Figure()
                    y0, y1 = (0, limite) if lado == "debajo" else (limite, max(hs[campo].max(), limite) * 1.1)
                    fig.add_hrect(y0=y0, y1=y1, fillcolor="red", opacity=0.08, line_width=0)
                    fig.add_hline(y=limite, line_dash="dot", line_color="red")
                    fig.add_trace(go.Scatter(x=hs["día"], y=hs[campo], mode="lines+markers", line_width=3))
                    fig.update_layout(title=titulo, height=260, margin=dict(l=10, r=10, t=40, b=10),
                                      xaxis_title="Día de enfermedad", showlegend=False)
                    col.plotly_chart(fig, width="stretch")

        st.subheader("3. 🗺️ Mapa de contagios: ¿dónde hacer la campaña de sanitización?")
        st.caption("Más rojo y más grande = más casos activos. Un caso en rojo pesa más que uno en verde.")
        peso = {"rojo": 3, "amarillo": 2, "verde": 1}
        df["peso"] = df._n.map(peso)
        zonas = (df.groupby("Zona").agg(casos=("Paciente", "size"), graves=("_n", lambda s: int((s == "rojo").sum())),
                                        lat=("lat", "mean"), lon=("lon", "mean"), puntos=("peso", "sum"))
                 .sort_values("puntos", ascending=False).reset_index())
        top = zonas.iloc[0]
        if top.casos >= 2:
            st.error(f"🧼 **Prioridad 1: {top.Zona}** · {top.casos} casos, {top.graves} en rojo 🔴. "
                     "Enviar brigada de fumigación, eliminación de criaderos y visita casa por casa.")
        for _, z in zonas.iloc[1:4].iterrows():
            if z.casos >= 2:
                st.warning(f"🧼 Prioridad {_ + 1}: **{z.Zona}** · {z.casos} casos, {z.graves} en rojo 🔴.")
        mx = max(zonas.puntos.max(), 1)
        zonas["radio"] = 500 + 2500 * zonas.puntos / mx
        zonas["color"] = zonas.puntos.apply(lambda v: [214, 69, 69, 120] if v / mx > 0.6 else
                                            ([232, 163, 23, 120] if v / mx > 0.3 else [31, 157, 85, 110]))
        zonas["etiqueta"] = zonas.Zona + " · " + zonas.casos.astype(str)
        span = max(df.lat.max() - df.lat.min(), df.lon.max() - df.lon.min(), 0.02)
        zoom = 12 if span < 0.05 else 10.5 if span < 0.2 else 8.5 if span < 1 else 7 if span < 2.5 else 6
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(latitude=float((df.lat.max() + df.lat.min()) / 2), longitude=float((df.lon.max() + df.lon.min()) / 2), zoom=zoom),
            layers=[
                pdk.Layer("HeatmapLayer", df, get_position="[lon, lat]", get_weight="peso", radiusPixels=60),
                pdk.Layer("ScatterplotLayer", zonas, get_position="[lon, lat]", get_fill_color="color",
                          get_radius="radio", pickable=True),
                pdk.Layer("ScatterplotLayer", df, get_position="[lon, lat]", get_fill_color="[0, 0, 0, 200]",
                          get_radius=120),
                pdk.Layer("TextLayer", zonas, get_position="[lon, lat]", get_text="etiqueta", get_size=15, character_set="auto", get_text_anchor="middle",
                          get_color=[20, 20, 20, 255]),
            ],
            tooltip={"text": "{Zona}: {casos} casos, {graves} en rojo 🔴"}))
        st.caption("Los puntos negros son pacientes; los círculos son las zonas a sanitizar.")

    # ---- estado de los centros
    st.subheader("4. 🏥 Estado de los centros de salud")
    st.caption("Datos de ejemplo. En la vida real cada centro reporta sus camas y su espera; "
               "la app suma los pacientes en rojo que ella misma asigna y avisa cuando un centro se llena.")
    tabla = pd.DataFrame([dict(
        Estado=f"{estados[c['id']]['emoji']} {estados[c['id']]['texto']}", Centro=c["nombre"], Tipo=c["tipo"],
        Ocupación=estados[c["id"]]["pct"], **{"Camas libres": estados[c["id"]]["libres"],
                                              "Espera (min)": c["espera_min"],
                                              "Graves enviados por la app": graves.get(c["id"], 0)})
        for c in sorted(cs, key=lambda c: -estados[c["id"]]["pct"])])
    st.dataframe(tabla, hide_index=True, width="stretch",
                 column_config={"Ocupación": st.column_config.ProgressColumn("Ocupación", format="percent", min_value=0, max_value=1)})

    with st.expander("✏️ Actualizar el estado de un centro (lo hace el centro)"):
        nombres_c = {c["nombre"]: c for c in cs}
        sel_c = nombres_c[st.selectbox("Centro", list(nombres_c), key="cen_sel")]
        k1, k2 = st.columns(2)
        ocup = k1.number_input(f"Camas ocupadas (de {sel_c['camas_total']})", 0, sel_c["camas_total"],
                               sel_c["camas_ocupadas"], key=f"oc{sel_c['id']}")
        espera = k2.number_input("Espera en emergencia (min)", 0, 600, sel_c["espera_min"], key=f"es{sel_c['id']}")
        b1, b2, b3 = st.columns(3)
        if b1.button("Guardar", key="cen_guardar", type="primary"):
            db.actualizar_centro(sel_c["id"], ocup, espera)
            st.rerun()
        if b2.button("🎬 Demo: saturar este centro", key="cen_saturar"):
            db.actualizar_centro(sel_c["id"], sel_c["camas_total"], 180)
            st.rerun()
        if b3.button("↩️ Restablecer todos", key="cen_reset"):
            for fila in centros.CENTROS_DEMO:
                original = nombres_c.get(fila[0])
                if original:
                    db.actualizar_centro(original["id"], fila[5], fila[6])
            st.rerun()

    if st.sidebar.button("🔄 Reiniciar datos de demo"):
        import datos_demo
        datos_demo.cargar()
        st.rerun()
