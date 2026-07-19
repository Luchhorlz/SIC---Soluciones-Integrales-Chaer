# Seeds

`taxonomy.json` es la taxonomía canónica aprobada: 29 categorías, 140 subcategorías y 1.392 servicios.

## Paquete demo aislado

`demo-data.json` configura un conjunto exclusivamente ficticio y removible. Genera exactamente tres identidades profesionales distintas por cada servicio canónico: 4.176 usuarios prestadores, perfiles y ofertas. Las filas se marcan con `is_demo`, usan correos bajo `.invalid` y las fichas públicas informan que sus datos son ficticios.

La previsualización web también conserva un respaldo determinista del mismo conjunto para que catálogo y buscador funcionen cuando PostgreSQL no está levantado. La prueba automatizada exige que ambas configuraciones sean idénticas.

Con PostgreSQL/PostGIS y el catálogo ya cargados:

```powershell
cd apps\api
$env:PYTHONPATH="src"
$env:DEMO_MODE="true"
.\.venv\Scripts\python.exe -m sic_api.modules.demo.seed --file ..\..\seeds\demo-data.json
```

El comando es idempotente. Para retirar todas las filas demo y sus relaciones:

```powershell
.\.venv\Scripts\python.exe -m sic_api.modules.demo.seed --file ..\..\seeds\demo-data.json --remove
```

El cargador se niega a ejecutarse con `APP_ENV=production`.
