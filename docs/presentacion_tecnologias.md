# Presentación del Sistema de Análisis de Sentimiento para Predicción de Tendencias Bursátiles

## Introducción

Este documento presenta una visión general del sistema de análisis de sentimiento para predicción de tendencias bursátiles, enfocándose en las tecnologías y herramientas utilizadas para su desarrollo e implementación. El sistema combina técnicas avanzadas de procesamiento de lenguaje natural, análisis de datos y visualización para proporcionar insights valiosos sobre la relación entre el sentimiento de las noticias y los movimientos del mercado de valores.

## Arquitectura del Sistema

El sistema sigue una arquitectura modular que permite la separación de responsabilidades y facilita el mantenimiento y la extensión. Los principales componentes son:

1. **Recopilación de Datos**: Obtención de datos históricos de acciones y noticias relacionadas.
2. **Preprocesamiento**: Limpieza y organización de los datos para su análisis.
3. **Análisis de Sentimiento**: Procesamiento de noticias para determinar su sentimiento.
4. **Correlación**: Análisis de la relación entre sentimiento y movimientos de precios.
5. **Visualización**: Presentación de resultados mediante gráficos y dashboards.
6. **Monitoreo de Costes**: Seguimiento y control de gastos en servicios de IA.

## Tecnologías Utilizadas

### 1. Lenguajes de Programación

- **Python 3.10+**: Lenguaje principal para todo el desarrollo del sistema, elegido por su amplio ecosistema de bibliotecas para ciencia de datos, procesamiento de lenguaje natural y aprendizaje automático.

### 2. Gestión de Dependencias y Entorno

- **uv**: Herramienta moderna y rápida para la gestión de paquetes y entornos virtuales de Python, que reemplaza a herramientas tradicionales como pip y virtualenv con mejor rendimiento.
- **ruff**: Linter de Python extremadamente rápido, escrito en Rust, que combina funcionalidades de flake8, isort, pyupgrade y otros, mejorando la calidad del código.

### 3. Almacenamiento de Datos

- **DuckDB**: Base de datos analítica embebida que proporciona un rendimiento excepcional para consultas OLAP (procesamiento analítico en línea), ideal para el análisis de grandes volúmenes de datos históricos de noticias y costes.
- **SQLite**: Base de datos relacional ligera utilizada para la integración con Apache Superset, proporcionando una interfaz SQL estándar para las visualizaciones.

### 4. APIs y Servicios Externos

- **Yahoo Finance API**: Proporciona datos históricos de precios de acciones, incluyendo precios de apertura, cierre, máximos, mínimos y volumen.
- **News API**: Permite la recopilación de noticias de diversas fuentes, filtradas por empresa y fecha.
- **OpenAI API (ChatGPT)**: Proporciona capacidades avanzadas de análisis de sentimiento con comprensión contextual y explicaciones detalladas.
- **Telegram API**: Permite enviar notificaciones y alertas a usuarios a través de la plataforma de mensajería Telegram.

### 5. Procesamiento de Lenguaje Natural

- **NLTK (Natural Language Toolkit)**: Biblioteca para procesamiento de lenguaje natural que proporciona herramientas para tokenización, stemming y análisis de sentimiento básico.
- **TextBlob**: Biblioteca de procesamiento de texto que simplifica tareas de NLP como análisis de sentimiento, clasificación y extracción de frases.
- **ChatGPT (GPT-3.5/GPT-4)**: Modelo de lenguaje avanzado utilizado para análisis de sentimiento contextual con capacidad de razonamiento y explicación.

### 6. Análisis de Datos y Visualización

- **Pandas**: Biblioteca fundamental para manipulación y análisis de datos estructurados, utilizada en todo el sistema para el procesamiento de datos.
- **NumPy**: Biblioteca para computación numérica que proporciona soporte para arrays y matrices multidimensionales y funciones matemáticas de alto nivel.
- **Matplotlib**: Biblioteca de visualización que proporciona gráficos estáticos, interactivos y animados en Python.
- **Seaborn**: Biblioteca de visualización estadística basada en Matplotlib que proporciona una interfaz de alto nivel para crear gráficos estadísticos atractivos.

### 7. Visualización de Dashboards

- **Apache Superset**: Plataforma de exploración de datos y visualización moderna, que permite crear dashboards interactivos y compartibles sin necesidad de programación.

### 8. Contenedorización

- **Docker**: Plataforma de contenedorización utilizada para empaquetar Apache Superset y sus dependencias, facilitando su despliegue y ejecución.
- **Docker Compose**: Herramienta para definir y ejecutar aplicaciones Docker multi-contenedor, utilizada para orquestar los servicios necesarios para Superset.

### 9. Configuración y Gestión

- **YAML**: Formato de serialización de datos legible por humanos utilizado para los archivos de configuración del sistema.
- **Logging**: Sistema de registro integrado para seguimiento de operaciones y depuración.
- **Scheduling**: Programación de tareas periódicas para actualizaciones automáticas.

## Apache Superset para Visualización de Dashboards

### Descripción General

Apache Superset es una plataforma de inteligencia empresarial web moderna, diseñada para explorar y visualizar datos. Ofrece una interfaz intuitiva para crear visualizaciones interactivas y dashboards sin necesidad de escribir código, lo que lo hace accesible para usuarios con diferentes niveles de experiencia técnica.

### Características Principales

1. **Exploración Visual de Datos**: Interfaz drag-and-drop para crear visualizaciones rápidamente.
2. **Amplia Variedad de Gráficos**: Más de 50 tipos de visualizaciones, desde gráficos básicos hasta mapas geoespaciales.
3. **SQL Lab**: Editor SQL interactivo para consultas ad-hoc.
4. **Dashboards Interactivos**: Creación de paneles con múltiples visualizaciones y filtros interactivos.
5. **Seguridad Granular**: Control de acceso a nivel de base de datos, tabla y columna.
6. **Escalabilidad**: Arquitectura que soporta desde pequeños conjuntos de datos hasta big data.

### Integración con el Sistema

El sistema de análisis de sentimiento se integra con Apache Superset a través de los siguientes componentes:

1. **Exportación de Datos**: El módulo `superset_integration.py` exporta los datos de sentimiento, correlación y costes a una base de datos SQLite compatible con Superset.
2. **Configuración Automática**: Genera archivos de configuración y scripts para facilitar la instalación y configuración de Superset.
3. **Actualización Automática**: Actualiza los datos en Superset después de cada análisis, manteniendo los dashboards siempre actualizados.

### Dashboards Implementados

El sistema configura tres dashboards principales en Superset:

1. **Análisis de Sentimiento por Empresa**:
   - Gráfico de líneas de sentimiento a lo largo del tiempo
   - Distribución de niveles de sentimiento
   - Tabla de noticias recientes con explicaciones
   - Filtros por empresa y rango de fechas

2. **Seguimiento de Costes de OpenAI**:
   - Gráfico de líneas de costes diarios
   - Distribución de costes por empresa
   - Métricas de tokens enviados vs. recibidos
   - Indicadores de coste total y promedio

3. **Correlación Sentimiento-Precio**:
   - Gráfico de dispersión de sentimiento vs. cambio de precio
   - Mapa de calor de correlaciones
   - Tabla de significancia estadística
   - Filtros por periodo de tiempo

## Flujo de Datos

El flujo de datos a través del sistema sigue estos pasos:

1. **Recopilación**: Datos de acciones de Yahoo Finance y noticias de News API.
2. **Almacenamiento**: Los datos se almacenan en DuckDB para un acceso eficiente.
3. **Preprocesamiento**: Limpieza, normalización y combinación de datos.
4. **Análisis**: Procesamiento con NLTK/TextBlob o ChatGPT según configuración.
5. **Correlación**: Cálculo de relaciones estadísticas entre sentimiento y precios.
6. **Exportación**: Los resultados se exportan a SQLite para Superset.
7. **Visualización**: Creación de dashboards interactivos en Superset.
8. **Notificación**: Envío de resúmenes y alertas por Telegram.

## Ventajas de las Tecnologías Seleccionadas

### DuckDB para Almacenamiento

- **Rendimiento Superior**: Hasta 100x más rápido que SQLite para consultas analíticas.
- **Integración con Pandas**: Perfecta interoperabilidad con DataFrames de Pandas.
- **Columnar Storage**: Optimizado para análisis de grandes volúmenes de datos.
- **Zero-Configuration**: No requiere servidor, ideal para aplicaciones embebidas.

### ChatGPT para Análisis de Sentimiento

- **Comprensión Contextual**: Entiende matices, sarcasmo y lenguaje técnico financiero.
- **Explicaciones Detalladas**: Proporciona razonamientos sobre el impacto de las noticias.
- **Adaptabilidad**: Funciona bien con diferentes estilos de escritura y fuentes de noticias.
- **Multilingüe**: Capacidad para analizar noticias en diferentes idiomas.

### Apache Superset para Visualización

- **No-Code**: Creación de dashboards sin necesidad de programación.
- **Interactividad**: Filtros y controles dinámicos para exploración de datos.
- **Compartible**: Fácil distribución de insights a stakeholders.
- **Extensible**: Soporte para múltiples bases de datos y tipos de visualización.

## Conclusión

El sistema de análisis de sentimiento para predicción de tendencias bursátiles representa una solución integral que combina tecnologías modernas de procesamiento de lenguaje natural, análisis de datos y visualización. La arquitectura modular y las tecnologías seleccionadas proporcionan un equilibrio entre rendimiento, flexibilidad y facilidad de uso.

La integración con Apache Superset eleva significativamente las capacidades de visualización del sistema, permitiendo a los usuarios explorar los datos de manera interactiva y obtener insights más profundos sobre la relación entre el sentimiento de las noticias y los movimientos del mercado.

Este enfoque tecnológico no solo cumple con los requisitos actuales del proyecto, sino que también establece una base sólida para futuras extensiones y mejoras, como la incorporación de modelos predictivos más avanzados o la integración con otras fuentes de datos.
