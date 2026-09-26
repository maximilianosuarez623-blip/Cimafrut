# CIMAFRUT unificado — versión mejorada

## Cambios principales
- Control de calidad con **una sola selección por criterio** (radio buttons) y botón bloqueado hasta completar todos.
- Frutas principales: Ciruela, Durazno, Pera, Damasco, Uva y Tomate.
- Variedad dependiente de la fruta mediante desplegables.
- Configuración de tipos de envase y peso vacío.
- Cálculo: **peso bruto del camión − tara del camión − tara total de envases = kilos netos**.
- Usuarios con roles: Administrador, General, Báscula/Ingreso, Precios, Control de calidad y Liquidaciones.
- El administrador puede crear y editar usuarios desde `/usuarios`.
- Se conserva la base SQLite del proyecto original y se agrega migración automática para los nuevos campos del usuario.

## Instalación en Windows PowerShell
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Abrir `http://127.0.0.1:5000`.

Usuario inicial: `admin` / `admin123`.

## Variedades
El catálogo inicial se armó como una base regional para Mendoza, priorizando referencias documentadas para el oasis Sur. Debe tomarse como catálogo inicial configurable, no como un censo exhaustivo de cada finca.
