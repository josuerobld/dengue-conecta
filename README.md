# DengueConecta 🦟

**Conecta al paciente con dengue que está en su casa con el médico del centro de salud, para que nadie se agrave sin que lo noten y el dengue no se siga contagiando en la colonia.**

Track: **DeepTech**. Apoyo para el médico, no reemplaza el diagnóstico.

## Correrla (5 minutos)
```bash
pip install -r requirements.txt
python datos_demo.py        # carga 15 pacientes ficticios (Pedro es el del pitch)
streamlit run app.py
```
- En la laptop: abre `http://localhost:8501`.
- En el celular (mismo wifi): abre la **Network URL** que imprime Streamlit. Así el paciente usa el celular y el médico la laptop, **con los mismos datos en vivo**.
- Leer fotos (OCR) es opcional: `pip install pytesseract` + instalar el programa Tesseract. Si no está, los números y el nombre de la medicina se escriben a mano.

## Pantalla de inicio
Al abrir la app sale primero la bienvenida con: **registrarme** (primera vez), **entrar con mi teléfono**, **soy médico** y un botón de **demo como Pedro**.

## Centros médicos y saturación
- Al registrarse, el paciente ve los centros más cercanos con distancia, estado (🟢 🟡 🔴) y el recomendado (el más cercano que tiene lo que necesita y no está colapsado). Al elegir, la app le asigna un médico por especialidad (ginecología si está embarazada, pediatría si es niño, infectología/medicina interna/general).
- Un centro está **colapsado** con ≥90 % de camas (incluyendo los pacientes en rojo que la app le asignó) o espera ≥120 min. Si el centro del paciente se colapsa, la app le avisa y le ofrece cambiarse a la mejor alternativa.
- El médico ve los centros colapsados, puede **derivar a todos y avisarles** (con WhatsApp) y actualizar la ocupación.
- ⚠️ Centros, camas, esperas y médicos del demo son **INVENTADOS**. En la vida real cada centro reportaría esos datos. Los centros reales cercanos se pueden ver (solo ubicación) desde OpenStreetMap.
- Para el demo: botón "🎬 Demo: saturar este centro" en la vista Médico.

## Archivos
| Archivo | Qué hace |
|---|---|
| `riesgo.py` | Reglas de riesgo basadas en el paper (leucopenia < 4,000, hematocrito +20 %, días 4-6) + signos de alarma OMS/OPS + condiciones de riesgo (diabetes, embarazo, hipertensión, riñón, corazón, obesidad, anticoagulantes, úlcera, edad < 1 o ≥ 65) con consejos por condición |
| `medicinas.py` | "¿Me lo tomo?": clasifica medicinas (AINEs/aspirina 🔴, antibióticos y corticoides 🟠, paracetamol 🟢) y lee hemogramas |
| `centros.py` | Centros médicos: cercanía (distancia y minutos en carro), saturación (camas + espera), centro recomendado, médico asignado por especialidad, centros reales vía OpenStreetMap |
| `db.py` | Base de datos SQLite compartida paciente/médico |
| `datos_demo.py` | Pacientes ficticios en Ciudad de Guatemala |
| `app.py` | La app: vista Paciente y vista Médico |

## Lo que deben hacer hoy
1. **Validar con un médico o la guía de la OPS** la lista de condiciones de riesgo y sus consejos (`CONDICIONES` en `riesgo.py`).
1. **Validar la tabla de medicinas** (`medicinas.py`) en una farmacia: marcas que se venden en Guatemala.
2. **Descargar la guía de dengue de la OPS** y citar la página de: paracetamol sí, AINEs/aspirina no, signos de alarma.
3. **Leer el paper principal** y ajustar umbrales de `riesgo.py` si usan otros.
4. **Datos propios:** 20-30 fotos de cajas de medicina reales y 5 hemogramas impresos (ficticios) para medir cuántos lee bien.
5. Mejorar lo visual y el texto para gente con poca lectura (íconos, audio).

## Papers
- **Principal:** Madewell et al., *Machine learning for predicting severe dengue in Puerto Rico*, Infectious Diseases of Poverty, feb 2025. DOI 10.1186/s40249-025-01273-0. Modelo AUC 97.1 % vs 74 % de los signos de alarma OMS; variables clave: hemoconcentración, leucopenia, días 4-6.
- **Automedicación:** Hoque et al., *Pre-Hospital Care and Referral Pattern among Admitted Patients with Dengue Fever in Dhaka Medical College Hospital*, Journal of Medicine 2025. DOI 10.3329/jom.v26i1.79152. 16.6 % antibióticos, 16.2 % hoja de papaya, 4.7 % corticoides antes de llegar al hospital.
- **Guía clínica:** guía de dengue de la OPS/OMS (descárguenla y citen la versión).

## Guion del demo (3 min)
1. **Problema (20 s):** "En epidemia, al paciente con dengue lo mandan a casa. Se automedica, no sabe leer su hemograma y el médico no sabe a quién llamar primero."
2. **Paciente (60 s), en el celular:** Pedro, zona 18, día 5. Escanea una caja de **ibuprofeno** → 🔴. Sube su hemograma del día 5 (botón "Simular" si falla la cámara).
3. **Médico (60 s), en la laptop:** Pedro salta a 🔴 con el motivo ("hematocrito subió 21 %"), gráfica de glóbulos blancos cayendo, botón WhatsApp. Mapa: "Zona 18: 9 casos, mandar brigada".
4. **Cierre (40 s):** "Pedro no pagó una consulta para que alguien leyera su examen, no se tomó lo que no debía, su médico lo vio a tiempo y su colonia fue fumigada. Un paper de 2025 mostró que estas señales predicen dengue grave mejor que los métodos actuales (97 % vs 74 %). Nosotros lo pusimos en manos de quien lo necesita."

Antes de presentar: botón **"Reiniciar datos de demo"** (vista Médico).

## Simulador de días y mapa de sanitización (demo)
- Pestaña **🧪 Mi hemograma** (paciente): "Simular mi chequeo y hemograma del día N" y "Pasar al día siguiente y simular" avanzan la enfermedad (días 1 a 6: fiebre, leucocitos y plaquetas bajando, hematocrito subiendo, signos de alarma el día 6). Barra lateral: "Simulador de días" (+1 día / volver a hoy). El reloj simulado lo comparten paciente y médico.
- Vista Médico, sección 3: mapa de calor de contagios con círculos por zona, lista de prioridad de sanitización (zona con más casos y graves primero).
