#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo principal del proyecto de análisis de sentimiento.
Coordina la ejecución de todos los componentes del sistema.
"""

import os
import sys
import argparse
from datetime import datetime
import schedule
import time
import logging

# Importar módulos del proyecto
from config_manager import config_manager
from stock_data_collector import StockDataCollector
from news_collector import NewsCollector
from data_preprocessor import DataPreprocessor
from sentiment_analyzer import SentimentAnalyzer
from chatgpt_sentiment_analyzer import ChatGPTSentimentAnalyzer
from sentiment_price_correlator import SentimentPriceCorrelator
from results_visualizer import ResultsVisualizer
from openai_cost_tracker import cost_tracker
from superset_integration import SupersetIntegration

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import nltk
    # Verificar si el recurso ya está descargado
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        # Si no está descargado, descargarlo
        nltk.download('punkt', quiet=True)
    
    # Verificar otros recursos que puedas necesitar
    # Por ejemplo, para análisis de sentimiento:
    try:
        nltk.data.find('sentiment/vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
except Exception as e:
    print(f"Error al inicializar NLTK: {str(e)}")

class SentimentAnalysisSystem:
    """Clase principal que coordina el sistema de análisis de sentimiento."""
    
    def __init__(self):
        """
        Inicializa el sistema de análisis de sentimiento.
        """
        # Obtener configuración
        self.config = config_manager.get_config()
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Crear directorios necesarios
        self.data_dir = os.path.join(self.project_dir, 'data')
        self.results_dir = os.path.join(self.data_dir, 'results')
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Determinar si se usa ChatGPT para el análisis de sentimiento
        self.use_chatgpt = config_manager.get_config('sentiment_analysis', 'use_chatgpt', False)
        
        # Determinar si se usa Superset para visualización
        self.use_superset = config_manager.get_config('superset', 'enabled', False)
        
        # Validar credenciales requeridas
        self._validate_credentials()
    
    def _validate_credentials(self):
        """
        Valida que todas las credenciales requeridas estén configuradas.
        """
        is_valid, missing = config_manager.validate_required_credentials()
        
        if not is_valid:
            logger.warning("Faltan las siguientes credenciales:")
            for cred in missing:
                logger.warning(f"- {cred}")
            
            logger.warning("Algunas funcionalidades pueden no estar disponibles.")
    
    def run_initial_analysis(self):
        """
        Ejecuta el análisis inicial completo.
        Recopila datos históricos, noticias, y realiza el análisis completo.
        """
        logger.info("=== Iniciando análisis inicial completo ===")
        start_time = datetime.now()
        
        # Paso 1: Recopilar datos históricos de acciones
        logger.info("--- Recopilando datos históricos de acciones ---")
        stock_collector = StockDataCollector()
        stock_collector.collect_historical_data()
        
        # Paso 2: Recopilar noticias históricas
        logger.info("--- Recopilando noticias históricas ---")
        news_collector = NewsCollector()
        news_collector.collect_historical_news()
        
        # Paso 3: Preprocesar datos
        logger.info("--- Preprocesando datos ---")
        preprocessor = DataPreprocessor()
        preprocessor.preprocess_all_data()
        
        # Paso 4: Analizar sentimiento (con ChatGPT o método tradicional)
        if self.use_chatgpt:
            logger.info("--- Analizando sentimiento con ChatGPT ---")
            analyzer = ChatGPTSentimentAnalyzer()
        else:
            logger.info("--- Analizando sentimiento con métodos tradicionales ---")
            analyzer = SentimentAnalyzer()
            
        analyzer.analyze_all_companies()
        
        # Paso 5: Analizar correlación
        logger.info("--- Analizando correlación entre sentimiento y precios ---")
        correlator = SentimentPriceCorrelator()
        correlator.analyze_all_companies()
        
        # Paso 6: Generar visualizaciones
        logger.info("--- Generando visualizaciones ---")
        visualizer = ResultsVisualizer()
        visualizer.visualize_all_companies()
        
        # Paso 7: Generar informe de costes si se usa ChatGPT
        if self.use_chatgpt and config_manager.get_config('cost_tracking', 'enabled', True):
            logger.info("--- Generando informe de costes de OpenAI ---")
            cost_report = cost_tracker.generate_cost_report()
            logger.info(f"Informe de costes generado en: {cost_report}")
            
            # Mostrar coste total
            total_cost = cost_tracker.get_total_cost()
            logger.info(f"Coste total acumulado: ${total_cost:.4f} USD")
        
        # Paso 8: Exportar datos para Superset si está habilitado
        if self.use_superset:
            logger.info("--- Exportando datos para Superset ---")
            superset = SupersetIntegration()
            export_results = superset.export_data_for_superset()
            logger.info(f"Datos exportados para Superset: {export_results}")
            
            # Generar instrucciones y configuración
            instructions_path = superset.generate_superset_instructions()
            docker_compose_path = superset.generate_docker_compose()
            
            logger.info(f"Instrucciones para Superset generadas en: {instructions_path}")
            logger.info(f"Archivo docker-compose.yml generado en: {docker_compose_path}")
        
        # Calcular tiempo total
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"=== Análisis inicial completado en {duration} ===")
    
    def run_daily_update(self):
        """
        Ejecuta la actualización diaria.
        Recopila nuevas noticias y actualiza el análisis.
        """
        logger.info("=== Iniciando actualización diaria ===")
        start_time = datetime.now()
        
        # Verificar límite de gasto diario si está configurado
        if self.use_chatgpt and config_manager.get_config('cost_tracking', 'enabled', True):
            daily_limit = config_manager.get_config('cost_tracking', 'daily_limit', 0)
            if daily_limit > 0:
                # Obtener costes del día actual
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                daily_costs = cost_tracker.get_costs_summary(start_date=today)
                
                if not daily_costs.empty:
                    daily_total = daily_costs['total_cost'].sum()
                    
                    # Verificar si se ha alcanzado el límite
                    if daily_total >= daily_limit:
                        logger.warning(f"Se ha alcanzado el límite diario de gasto (${daily_limit:.2f}). Usando análisis tradicional.")
                        self.use_chatgpt = False
                    
                    # Verificar si se ha alcanzado el umbral de alerta
                    alert_threshold = config_manager.get_config('cost_tracking', 'alert_threshold', 80)
                    threshold_value = (daily_limit * alert_threshold) / 100
                    
                    if daily_total >= threshold_value:
                        logger.warning(f"Alerta: Se ha alcanzado el {alert_threshold}% del límite diario de gasto (${daily_total:.2f}/{daily_limit:.2f}).")
        
        # Paso 1: Actualizar datos de acciones (últimos 2 días)
        logger.info("--- Actualizando datos de acciones ---")
        stock_collector = StockDataCollector()
        stock_collector.collect_historical_data()
        
        # Paso 2: Actualizar noticias (últimos 2 días)
        logger.info("--- Actualizando noticias ---")
        news_collector = NewsCollector()
        news_collector.update_news()
        
        # Paso 3: Preprocesar datos
        logger.info("--- Preprocesando datos ---")
        preprocessor = DataPreprocessor()
        preprocessor.preprocess_all_data()
        
        # Paso 4: Actualizar análisis de sentimiento (con ChatGPT o método tradicional)
        if self.use_chatgpt:
            logger.info("--- Actualizando análisis de sentimiento con ChatGPT ---")
            analyzer = ChatGPTSentimentAnalyzer()
        else:
            logger.info("--- Actualizando análisis de sentimiento con métodos tradicionales ---")
            analyzer = SentimentAnalyzer()
            
        analyzer.analyze_all_companies()
        
        # Paso 5: Actualizar análisis de correlación
        logger.info("--- Actualizando análisis de correlación ---")
        correlator = SentimentPriceCorrelator()
        correlator.analyze_all_companies()
        
        # Paso 6: Actualizar visualizaciones
        logger.info("--- Actualizando visualizaciones ---")
        visualizer = ResultsVisualizer()
        visualizer.visualize_all_companies()
        
        # Paso 7: Generar informe de costes si se usa ChatGPT y está configurado
        if self.use_chatgpt and config_manager.get_config('cost_tracking', 'daily_report', True):
            logger.info("--- Generando informe diario de costes de OpenAI ---")
            cost_report = cost_tracker.generate_cost_report()
            logger.info(f"Informe de costes generado en: {cost_report}")
            
            # Mostrar coste total
            total_cost = cost_tracker.get_total_cost()
            daily_costs = cost_tracker.get_daily_costs(1)
            
            if not daily_costs.empty:
                daily_total = daily_costs['total_cost'].sum()
                logger.info(f"Coste de hoy: ${daily_total:.4f} USD")
            
            logger.info(f"Coste total acumulado: ${total_cost:.4f} USD")
        
        # Paso 8: Actualizar datos para Superset si está habilitado y configurado
        if self.use_superset and config_manager.get_config('superset', 'auto_update', True):
            logger.info("--- Actualizando datos para Superset ---")
            superset = SupersetIntegration()
            export_results = superset.export_data_for_superset()
            logger.info(f"Datos actualizados para Superset: {export_results}")
        
        # Calcular tiempo total
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"=== Actualización completada en {duration} ===")
    
    def schedule_updates(self):
        """
        Programa actualizaciones periódicas según la configuración.
        """
        update_interval = config_manager.get_config('general', 'update_interval', 'daily')
        
        if update_interval == "daily":
            # Actualizar una vez al día a las 8:00
            schedule.every().day.at("08:00").do(self.run_daily_update)
            logger.info("Actualizaciones programadas: diariamente a las 08:00")
        elif update_interval == "6hours":
            # Actualizar cada 6 horas
            schedule.every(6).hours.do(self.run_daily_update)
            logger.info("Actualizaciones programadas: cada 6 horas")
        else:
            # Por defecto, actualizar diariamente
            schedule.every().day.at("08:00").do(self.run_daily_update)
            logger.info("Actualizaciones programadas: diariamente a las 08:00 (valor por defecto)")
        
        logger.info("Servicio de actualización iniciado. Presiona Ctrl+C para detener.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Comprobar cada minuto
        except KeyboardInterrupt:
            logger.info("Servicio de actualización detenido.")

def main():
    """Función principal del programa."""
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description='Sistema de Análisis de Sentimiento para Predicción de Tendencias Bursátiles')
    parser.add_argument('--init', action='store_true', help='Ejecutar análisis inicial completo')
    parser.add_argument('--update', action='store_true', help='Ejecutar actualización diaria')
    parser.add_argument('--schedule', action='store_true', help='Programar actualizaciones periódicas')
    parser.add_argument('--use-chatgpt', action='store_true', help='Forzar el uso de ChatGPT para el análisis de sentimiento')
    parser.add_argument('--cost-report', action='store_true', help='Generar informe de costes de OpenAI')
    parser.add_argument('--superset-export', action='store_true', help='Exportar datos para Superset')
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Crear instancia del sistema
    system = SentimentAnalysisSystem()
    
    # Si se especifica --use-chatgpt, forzar el uso de ChatGPT
    if args.use_chatgpt:
        system.use_chatgpt = True
        logger.info("Forzando el uso de ChatGPT para el análisis de sentimiento")
    
    # Ejecutar según los argumentos
    if args.init:
        system.run_initial_analysis()
    elif args.update:
        system.run_daily_update()
    elif args.schedule:
        system.schedule_updates()
    elif args.cost_report:
        # Generar informe de costes
        if config_manager.get_config('cost_tracking', 'enabled', True):
            logger.info("Generando informe de costes de OpenAI")
            cost_report = cost_tracker.generate_cost_report()
            
            total_cost = cost_tracker.get_total_cost()
            costs_by_symbol = cost_tracker.get_costs_by_symbol()
            daily_costs = cost_tracker.get_daily_costs(30)
            
            logger.info(f"Informe de costes generado en: {cost_report}")
            logger.info(f"Coste total acumulado: ${total_cost:.4f} USD")
            
            if not daily_costs.empty:
                logger.info("Costes de los últimos 30 días:")
                for _, row in daily_costs.head(5).iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date'])
                    logger.info(f"  {date_str}: ${row['total_cost']:.4f} USD ({row['total_tokens']} tokens)")
                
                if len(daily_costs) > 5:
                    logger.info(f"  ... y {len(daily_costs) - 5} días más (ver informe completo)")
            
            if not costs_by_symbol.empty:
                logger.info("Costes por empresa (Top 5):")
                for _, row in costs_by_symbol.head(5).iterrows():
                    logger.info(f"  {row['symbol']}: ${row['total_cost']:.4f} USD ({row['requests']} solicitudes)")
        else:
            logger.warning("El seguimiento de costes no está habilitado en la configuración")
    elif args.superset_export:
        # Exportar datos para Superset
        if config_manager.get_config('superset', 'enabled', True):
            logger.info("Exportando datos para Superset")
            superset = SupersetIntegration()
            export_results = superset.export_data_for_superset()
            
            # Generar instrucciones y configuración
            instructions_path = superset.generate_superset_instructions()
            docker_compose_path = superset.generate_docker_compose()
            
            logger.info(f"Datos exportados para Superset: {export_results}")
            logger.info(f"Instrucciones para Superset generadas en: {instructions_path}")
            logger.info(f"Archivo docker-compose.yml generado en: {docker_compose_path}")
        else:
            logger.warning("La integración con Superset no está habilitada en la configuración")
    else:
        # Si no se especifica ninguna acción, mostrar ayuda
        parser.print_help()

if __name__ == "__main__":
    # Simula la entrada de la línea de comandos con --init
    sys.argv = ['main.py', '--init']  # Modifica sys.argv para incluir --init
    main()
