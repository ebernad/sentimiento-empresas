# Análisis de Sentimiento para Predicción de Tendencias Bursátiles

Este proyecto implementa un sistema de análisis de sentimiento de noticias utilizando IA para prever posibles tendencias del mercado (subida o bajada) de acciones de empresas seleccionadas.

## Características

- Recopilación de datos históricos de acciones y noticias
- Análisis de sentimiento de noticias con cinco niveles (muy negativo, negativo, neutro, positivo, muy positivo)
- Análisis avanzado con ChatGPT con contexto histórico configurable
- Almacenamiento eficiente con DuckDB para consultas analíticas rápidas
- Seguimiento y control de costes de OpenAI con límites de gasto configurables
- Visualización avanzada con Apache Superset para dashboards interactivos
- Correlación entre sentimiento y movimientos de precios
- Actualizaciones periódicas (diarias o cada 6 horas)
- Notificaciones por Telegram con explicaciones detalladas
- Gestión segura de credenciales en archivos YAML separados

## Requisitos

- Python 3.8 o superior
- Conexión a Internet para obtener datos de acciones y noticias
- API key de OpenAI para el análisis con ChatGPT (opcional)
- Docker y Docker Compose para Apache Superset (opcional)

## Instalación

1. Clona este repositorio:
   ```
   git clone https://github.com/tu-usuario/analisis-sentimiento-acciones.git
   cd analisis-sentimiento-acciones
   ```

2. Ejecuta el script de instalación:
   ```
   python install.py
   ```

   Este script:
   - Verifica la versión de Python
   - Instala uv si no está instalado
   - Crea un entorno virtual
   - Instala todas las dependencias necesarias
   - Configura ruff para el linting del código

## Configuración

El sistema utiliza dos archivos YAML para la configuración:

### 1. Configuración General (config/config.yaml)

Este archivo contiene la configuración general del proyecto:

```yaml
# Configuración general del proyecto
general:
  update_interval: "daily"  # "daily" o "6hours"
  historical_years: 3       # Periodo histórico inicial en años (1-5)

# Lista de empresas a analizar
companies:
  - symbol: "AAPL"
    name: "Apple Inc."
    region: "US"
  - symbol: "MSFT"
    name: "Microsoft Corporation"
    region: "US"
  # Añade más empresas según necesites

# Configuración del análisis de sentimiento
sentiment_analysis:
  use_chatgpt: true  # Usar ChatGPT para el análisis
  # Otras configuraciones...

# Configuración de la base de datos
database:
  type: "duckdb"
  filename: "news_database.duckdb"

# Configuración del seguimiento de costes de OpenAI
cost_tracking:
  enabled: true
  daily_report: true
  daily_limit: 5.0
  alert_threshold: 80
  save_details: true

# Configuración de Superset
superset:
  enabled: true
  port: 8088
  auto_update: true
  dashboards:
    - name: "Análisis de Sentimiento por Empresa"
      enabled: true
    - name: "Seguimiento de Costes de OpenAI"
      enabled: true
    - name: "Correlación Sentimiento-Precio"
      enabled: true
```

### 2. Credenciales (config/credentials.yaml)

Este archivo contiene todas las claves de API y credenciales sensibles:

```yaml
# API de noticias
news_api:
  api_key: "YOUR_NEWS_API_KEY"

# Telegram
telegram:
  token: "YOUR_TELEGRAM_TOKEN"
  chat_id: "YOUR_CHAT_ID"

# OpenAI para ChatGPT
openai:
  api_key: "YOUR_OPENAI_API_KEY"
  model: "gpt-3.5-turbo"
  max_daily_calls: 100
  historical_context_range: "week"  # "week", "month", "year" o "all"
```

## Uso

Activa el entorno virtual:

```
# En Linux/macOS
source .venv/bin/activate

# En Windows
.venv\Scripts\activate.bat
```

### Análisis inicial completo

Para ejecutar un análisis inicial completo que recopile datos históricos y realice el análisis:

```
python src/main.py --init
```

### Actualización diaria

Para ejecutar una actualización que recopile nuevas noticias y actualice el análisis:

```
python src/main.py --update
```

### Programar actualizaciones periódicas

Para programar actualizaciones periódicas según la configuración:

```
python src/main.py --schedule
```

### Forzar el uso de ChatGPT

Para forzar el uso de ChatGPT independientemente de la configuración:

```
python src/main.py --init --use-chatgpt
```

### Generar informe de costes

Para generar un informe detallado de los costes de OpenAI:

```
python src/main.py --cost-report
```

### Exportar datos para Superset

Para exportar los datos a un formato compatible con Apache Superset:

```
python src/main.py --superset-export
```

## Estructura del Proyecto

```
proyecto_analisis_sentimiento/
├── config/
│   ├── config.yaml         # Configuración general del proyecto
│   └── credentials.yaml    # Credenciales y claves de API
├── data/
│   ├── stocks/             # Datos de acciones
│   ├── news/               # Datos de noticias (respaldo)
│   ├── news_database.duckdb # Base de datos DuckDB para noticias
│   ├── openai_costs.duckdb # Base de datos DuckDB para costes de OpenAI
│   ├── superset_data.db    # Base de datos SQLite para Superset
│   ├── processed/          # Datos preprocesados
│   └── results/            # Resultados del análisis
│       ├── correlation/    # Análisis de correlación
│       └── visualization/  # Visualizaciones
├── src/
│   ├── main.py                      # Módulo principal
│   ├── config_manager.py            # Gestor de configuración y credenciales
│   ├── stock_data_collector.py      # Recopilación de datos de acciones
│   ├── news_collector.py            # Recopilación de noticias
│   ├── news_database.py             # Gestión de base de datos DuckDB para noticias
│   ├── openai_cost_tracker.py       # Seguimiento y control de costes de OpenAI
│   ├── data_preprocessor.py         # Preprocesamiento de datos
│   ├── sentiment_analyzer.py        # Análisis de sentimiento tradicional
│   ├── chatgpt_sentiment_analyzer.py # Análisis de sentimiento con ChatGPT
│   ├── sentiment_price_correlator.py # Correlación sentimiento-precio
│   ├── results_visualizer.py        # Visualización de resultados
│   └── superset_integration.py      # Integración con Apache Superset
├── superset/                # Archivos de configuración para Superset
│   ├── docker-compose.yml   # Configuración de Docker para Superset
│   └── superset_setup.md    # Instrucciones para configurar Superset
├── tests/                  # Pruebas unitarias
├── docs/                   # Documentación adicional
│   └── presentacion_tecnologias.md  # Presentación de tecnologías utilizadas
├── install.py              # Script de instalación
├── requirements.txt        # Dependencias del proyecto
└── pyproject.toml          # Configuración de ruff
```

## Componentes Principales

### 1. Gestión de Configuración

- **config_manager.py**: Proporciona una interfaz unificada para acceder a todas las configuraciones y credenciales del proyecto, con validación de credenciales requeridas.

### 2. Almacenamiento de Datos

- **news_database.py**: Gestiona la base de datos DuckDB para almacenamiento eficiente de noticias, con funciones para consultas analíticas rápidas y filtrado por fecha o contenido.
- **openai_cost_tracker.py**: Gestiona el seguimiento y control de costes de OpenAI, almacenando información detallada en DuckDB.

### 3. Recopilación de Datos

- **stock_data_collector.py**: Obtiene datos históricos de acciones utilizando la API de Yahoo Finance.
- **news_collector.py**: Recopila noticias relacionadas con las empresas seleccionadas y las almacena en DuckDB.

### 4. Preprocesamiento de Datos

- **data_preprocessor.py**: Limpia y prepara los datos de acciones y noticias para el análisis.

### 5. Análisis de Sentimiento

- **sentiment_analyzer.py**: Análisis tradicional utilizando NLTK y TextBlob.
- **chatgpt_sentiment_analyzer.py**: Análisis avanzado utilizando ChatGPT con contexto histórico.

### 6. Correlación y Visualización

- **sentiment_price_correlator.py**: Analiza la correlación entre el sentimiento y los movimientos de precios.
- **results_visualizer.py**: Genera visualizaciones detalladas de los resultados.
- **superset_integration.py**: Integra el sistema con Apache Superset para dashboards interactivos.

### 7. Coordinación

- **main.py**: Coordina la ejecución de todos los componentes y proporciona una interfaz de línea de comandos.

## Análisis de Sentimiento con ChatGPT

El sistema permite utilizar ChatGPT para un análisis de sentimiento más avanzado y contextualizado:

1. **Análisis Contextual**: Proporciona a ChatGPT el contexto histórico de noticias anteriores para un análisis más informado.

2. **Rangos de Contexto Configurables**: Permite seleccionar diferentes rangos de fechas para el contexto histórico:
   - Última semana (`week`)
   - Último mes (`month`)
   - Último año (`year`)
   - Todo el histórico disponible (`all`)

3. **Explicaciones Detalladas**: ChatGPT proporciona explicaciones sobre por qué una noticia podría afectar positiva o negativamente al precio de la acción.

4. **Notificaciones Enriquecidas**: Las notificaciones por Telegram incluyen explicaciones detalladas del análisis.

## Almacenamiento con DuckDB

El sistema utiliza DuckDB para un almacenamiento eficiente de noticias históricas y costes de OpenAI:

1. **Consultas Analíticas Rápidas**: Optimizado para análisis de datos, permitiendo consultas complejas sobre el histórico de noticias.

2. **Indexación y Búsqueda**: Índices para búsquedas rápidas por fecha, empresa o contenido.

3. **Filtrado Eficiente**: Permite filtrar noticias por rango de fechas o palabras clave con alto rendimiento.

4. **Menor Uso de Memoria**: Procesamiento eficiente de grandes volúmenes de noticias históricas.

5. **Integración con Pandas**: Perfecta integración con Pandas para análisis posterior.

## Seguimiento y Control de Costes de OpenAI

El sistema incluye un módulo completo para el seguimiento y control de costes de la API de OpenAI:

1. **Seguimiento Detallado**: Registra información detallada sobre cada llamada a la API, incluyendo tokens enviados y recibidos, costes asociados, y metadatos como símbolo de empresa y fecha de la noticia.

2. **Cálculo Preciso de Costes**: Calcula los costes según los precios actuales de diferentes modelos de OpenAI (gpt-3.5-turbo, gpt-4, gpt-4-turbo).

3. **Límites de Gasto Configurables**: Permite establecer límites diarios de gasto y umbrales de alerta para controlar los costes.

4. **Informes Detallados**: Genera informes detallados con análisis de costes por empresa, por día, y totales acumulados.

5. **Recomendaciones de Optimización**: Proporciona recomendaciones para optimizar el uso y reducir costes.

## Visualización con Apache Superset

El sistema se integra con Apache Superset para proporcionar dashboards interactivos y avanzados:

1. **Dashboards Interactivos**: Permite crear paneles personalizados con múltiples visualizaciones y filtros interactivos.

2. **Exploración Visual**: Interfaz intuitiva para explorar los datos sin necesidad de programación.

3. **Múltiples Visualizaciones**: Soporte para diversos tipos de gráficos, desde líneas y barras hasta mapas de calor y gráficos de dispersión.

4. **Actualización Automática**: Los datos se actualizan automáticamente después de cada análisis.

5. **Despliegue con Docker**: Configuración lista para desplegar Superset con Docker Compose.

### Dashboards Implementados

El sistema configura tres dashboards principales en Superset:

1. **Análisis de Sentimiento por Empresa**: Visualización del sentimiento de noticias por empresa a lo largo del tiempo.

2. **Seguimiento de Costes de OpenAI**: Monitoreo detallado de costes por día, empresa y tipo de solicitud.

3. **Correlación Sentimiento-Precio**: Análisis visual de la relación entre sentimiento y movimientos de precios.

## Seguridad de Credenciales

El sistema separa las credenciales y claves de API en un archivo YAML dedicado:

1. **Separación de Configuración**: Las credenciales sensibles se mantienen separadas de la configuración general.

2. **Validación de Credenciales**: El sistema valida que todas las credenciales requeridas estén configuradas correctamente.

3. **Acceso Centralizado**: Interfaz unificada para acceder a todas las configuraciones y credenciales.

## Resultados

Los resultados del análisis se guardan en el directorio `data/results/`:

- Archivos CSV con datos de sentimiento (tradicional y ChatGPT)
- Informes de correlación en formato Markdown
- Visualizaciones en formato PNG
- Informes de costes de OpenAI en formato Markdown
- Base de datos SQLite para Superset con todos los datos integrados

## Documentación Adicional

Para una descripción detallada de las tecnologías utilizadas en el proyecto, consulta el documento [presentacion_tecnologias.md](docs/presentacion_tecnologias.md) que incluye:

- Arquitectura del sistema
- Descripción detallada de cada tecnología
- Ventajas de las tecnologías seleccionadas
- Flujo de datos a través del sistema
- Detalles sobre la integración con Apache Superset

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.
