# Guía de instalación

Requisitos: **Python 3.11 o superior** y conexión a internet para instalar dependencias.

## Windows (recomendado)

1. Instale Python desde [python.org](https://www.python.org/downloads/). En el instalador, marque **“Add python.exe to PATH”**.

2. Abra **PowerShell** o **Símbolo del sistema** en la carpeta del proyecto.

3. Cree y active el entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

4. Instale el proyecto:

```powershell
python -m pip install --upgrade pip
pip install -e .
```

5. Compruebe la instalación:

```powershell
python -c "import vfiic_kpis; print('OK')"
```

## Windows con WSL

1. En WSL, instale Python 3.11+ (`sudo apt install python3 python3-venv python3-pip` en Ubuntu).

2. Navegue a la carpeta del proyecto (ruta bajo `/mnt/c/...` si el repo está en disco C:).

3. Mismos pasos que en Linux (ver abajo). Use los archivos Excel en `inputs/` desde Windows o copiándolos al árbol de WSL.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

## Siguiente paso

Vaya a [guia-operativa.md](guia-operativa.md) para copiar insumos y generar reportes.
