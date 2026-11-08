# Genera el ejecutable (.exe) de la app del USUARIO y lo empaqueta en un .zip.
#
# ANTES DE LA PRIMERA VEZ (y cada vez que rote las claves):
#   python generar_clave_embebida.py
#
# Uso (desde la carpeta backend, con el entorno virtual activado):
#   .\construir_exe.ps1            -> version final, sin ventana de consola
#   .\construir_exe.ps1 -Consola   -> version de prueba, con consola para ver errores
param([switch]$Consola)

$ErrorActionPreference = "Stop"

foreach ($f in @("modelo_senas.joblib", "modelo_senas.joblib.sig", "clave_publica_embebida.py")) {
    if (-not (Test-Path $f)) {
        throw "Falta $f. Si es la clave embebida, ejecute primero: python generar_clave_embebida.py"
    }
}

pip install pyinstaller

$modo = if ($Consola) { "--console" } else { "--windowed" }

pyinstaller --noconfirm --clean --name DetectorSenas $modo --collect-data mediapipe --collect-binaries mediapipe main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo. Revisa los mensajes de arriba." }

# El modelo y su firma van junto al .exe (asi se pueden actualizar sin recompilar).
# La clave publica YA esta incrustada en el .exe: no hace falta copiar el .pem.
Copy-Item modelo_senas.joblib, modelo_senas.joblib.sig -Destination dist\DetectorSenas\

Compress-Archive -Path dist\DetectorSenas -DestinationPath DetectorSenas_win64.zip -Force
Write-Host ""
Write-Host "Listo: DetectorSenas_win64.zip"