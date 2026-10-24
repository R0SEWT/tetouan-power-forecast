"""En Colab, en la misma máquina de la ingesta del IEOD: exógenas, línea base y copia al Drive.

Se corre desde un clon del repo, en el kernel del notebook 00_medallon_coes, cuando termina la descarga:

    !git clone -q -b feature/nucleo-sein https://github.com/R0SEWT/tetouan-power-forecast /content/tpf
    %run /content/tpf/experimentos/sein/noche.py

Reinstala el paquete de la rama (el kernel tenía otra versión), baja las exógenas, arma el silver de áreas si
falta, corre la línea base en la validación de 2025, ejecuta el notebook 01 y deja todo esperando el permiso
del Drive para copiarlo. La
espera mantiene ocupada la sesión, así Colab no la recicla antes de que alguien acepte el permiso.
"""

import os
import subprocess
import sys
from pathlib import Path

RAMA = "feature/nucleo-sein"
DATOS = "/content/datos"

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--force-reinstall", "--no-deps",
                f"git+https://github.com/R0SEWT/tetouan-power-forecast@{RAMA}"], check=True)
for nombre in [m for m in sys.modules if m.startswith(("tetouan_power_forecast", "experimentos"))]:
    del sys.modules[nombre]  # que los import de abajo lean la versión recién instalada
os.environ["TETOUAN_DATA"] = DATOS
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # la raíz del clon, para experimentos/

from experimentos.sein import linea_base
from tetouan_power_forecast import coes, exogenas
from tetouan_power_forecast.medallon import copiar_al_drive

if not (Path(DATOS) / "coes/silver/demanda_areas.parquet").exists():
    coes.silver_areas()
exogenas.bronze_nino()
exogenas.bronze_saidi()
exogenas.bronze_eventos()
exogenas.bronze_era5()
exogenas.silver_exogenas()
linea_base.main()
# El notebook 01 con los datos reales; el ejecutado se copia al Drive con lo demás
salida = Path(DATOS) / "reportes" / "notebooks"
salida.mkdir(parents=True, exist_ok=True)
subprocess.run(["jupyter", "nbconvert", "--to", "notebook", "--execute", "--allow-errors",
                "--ExecutePreprocessor.timeout=3600", "--output-dir", str(salida),
                str(Path(__file__).resolve().parents[2] / "notebooks" / "01_sein_datos_preparacion.ipynb")],
               env={**os.environ, "TETOUAN_DATA": DATOS}, check=False)
for carpeta in ("coes", "exogenas", "reportes"):
    copiar_al_drive(f"{DATOS}/{carpeta}", carpeta)
