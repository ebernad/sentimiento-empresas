#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para analizar la correlación entre el sentimiento de las noticias y los movimientos de precios.
"""

import os
import sys
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

class SentimentPriceCorrelator:
    """Clase para analizar la correlación entre sentimiento y movimientos de precios."""
    
    def __init__(self, config_path):
        """
        Inicializa el correlador de sentimiento y precios.
        
        Args:
            config_path (str): Ruta al archivo de configuración YAML.
        """
        self.config = self._load_config(config_path)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.results_dir = os.path.join(self.data_dir, 'results')
        self.correlation_dir = os.path.join(self.results_dir, 'correlation')
        os.makedirs(self.correlation_dir, exist_ok=True)
        
        # Configurar colores para visualización
        self.colors = self.config['visualization']['colors']
    
    def _load_config(self, config_path):
        """
        Carga la configuración desde el archivo YAML.
        
        Args:
            config_path (str): Ruta al archivo de configuración.
            
        Returns:
            dict: Configuración cargada.
        """
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    def analyze_all_companies(self):
        """
        Analiza la correlación para todas las empresas configuradas.
        
        Returns:
            dict: Resultados del análisis de correlación por símbolo de empresa.
        """
        results = {}
        
        for company in self.config['companies']:
            symbol = company['symbol']
            name = company['name']
            
            print(f"Analizando correlación para {name} ({symbol})...")
            
            try:
                # Cargar datos de sentimiento
                sentiment_data = self._load_sentiment_data(symbol)
                
                if sentiment_data is not None:
                    # Analizar correlación
                    correlation_results = self._analyze_correlation(sentiment_data, symbol, name)
                    results[symbol] = correlation_results
                
            except Exception as e:
                print(f"Error al analizar correlación para {symbol}: {str(e)}")
        
        return results
    
    def _load_sentiment_data(self, symbol):
        """
        Carga los datos de sentimiento.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con datos de sentimiento.
        """
        file_path = os.path.join(self.results_dir, f"{symbol}_sentiment.csv")
        
        if not os.path.exists(file_path):
            print(f"No se encontraron datos de sentimiento para {symbol}")
            return None
        
        # Cargar datos
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        return df
    
    def _analyze_correlation(self, df, symbol, company_name):
        """
        Analiza la correlación entre sentimiento y movimientos de precios.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            dict: Resultados del análisis de correlación.
        """
        # Crear copia para no modificar el original
        corr_df = df.copy()
        
        # Convertir niveles de sentimiento a valores numéricos
        sentiment_map = {
            'muy_malo': -2,
            'malo': -1,
            'neutro': 0,
            'bueno': 1,
            'muy_bueno': 2
        }
        
        corr_df['sentiment_numeric'] = corr_df['sentiment_level'].map(sentiment_map)
        
        # Calcular cambios futuros en el precio (1, 3 y 5 días)
        for days in [1, 3, 5]:
            corr_df[f'price_change_{days}d'] = corr_df['close'].pct_change(periods=days).shift(-days) * 100
        
        # Eliminar filas con valores NaN
        corr_df.dropna(inplace=True)
        
        # Calcular correlaciones
        correlations = {}
        for days in [1, 3, 5]:
            # Correlación de Pearson
            pearson_corr, pearson_p = stats.pearsonr(
                corr_df['sentiment_numeric'], 
                corr_df[f'price_change_{days}d']
            )
            
            # Correlación de Spearman (ranking)
            spearman_corr, spearman_p = stats.spearmanr(
                corr_df['sentiment_numeric'], 
                corr_df[f'price_change_{days}d']
            )
            
            correlations[f'{days}d'] = {
                'pearson': pearson_corr,
                'pearson_p': pearson_p,
                'spearman': spearman_corr,
                'spearman_p': spearman_p
            }
        
        # Calcular estadísticas por nivel de sentimiento
        sentiment_stats = {}
        for level in ['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno']:
            level_data = corr_df[corr_df['sentiment_level'] == level]
            
            if not level_data.empty:
                stats_dict = {}
                for days in [1, 3, 5]:
                    changes = level_data[f'price_change_{days}d']
                    stats_dict[f'{days}d'] = {
                        'mean': changes.mean(),
                        'median': changes.median(),
                        'std': changes.std(),
                        'min': changes.min(),
                        'max': changes.max(),
                        'positive_pct': (changes > 0).mean() * 100,
                        'count': len(changes)
                    }
                sentiment_stats[level] = stats_dict
        
        # Crear gráficos
        self._create_correlation_plots(corr_df, correlations, sentiment_stats, symbol, company_name)
        
        # Guardar resultados
        results = {
            'correlations': correlations,
            'sentiment_stats': sentiment_stats
        }
        
        # Guardar como CSV para referencia
        corr_df.to_csv(os.path.join(self.correlation_dir, f"{symbol}_correlation_data.csv"))
        
        # Crear informe de texto
        self._create_correlation_report(results, symbol, company_name)
        
        return results
    
    def _create_correlation_plots(self, df, correlations, sentiment_stats, symbol, company_name):
        """
        Crea gráficos de correlación entre sentimiento y movimientos de precios.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de correlación.
            correlations (dict): Resultados de correlación.
            sentiment_stats (dict): Estadísticas por nivel de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
        """
        # Configurar estilo de seaborn
        sns.set(style="whitegrid")
        
        # 1. Gráfico de dispersión: Sentimiento vs Cambio de Precio (3 días)
        plt.figure(figsize=(12, 8))
        
        # Crear un mapa de colores para los puntos
        color_map = {
            'muy_malo': self.colors['muy_malo'],
            'malo': self.colors['malo'],
            'neutro': self.colors['neutro'],
            'bueno': self.colors['bueno'],
            'muy_bueno': self.colors['muy_bueno']
        }
        
        # Asignar colores a cada punto
        point_colors = df['sentiment_level'].map(color_map)
        
        # Crear gráfico de dispersión
        plt.scatter(
            df['sentiment_numeric'], 
            df['price_change_3d'],
            c=point_colors,
            alpha=0.7,
            s=50
        )
        
        # Añadir línea de tendencia
        z = np.polyfit(df['sentiment_numeric'], df['price_change_3d'], 1)
        p = np.poly1d(z)
        plt.plot(
            [-2, 2], 
            [p(-2), p(2)], 
            "r--", 
            linewidth=2
        )
        
        # Añadir etiquetas y título
        plt.xlabel('Nivel de Sentimiento', fontsize=12)
        plt.ylabel('Cambio de Precio a 3 Días (%)', fontsize=12)
        plt.title(f'Correlación entre Sentimiento y Cambio de Precio para {company_name} ({symbol})', fontsize=14)
        
        # Añadir leyenda
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['muy_malo'], label='Muy Negativo', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['malo'], label='Negativo', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['neutro'], label='Neutro', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['bueno'], label='Positivo', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['muy_bueno'], label='Muy Positivo', markersize=10)
        ]
        plt.legend(handles=legend_elements, loc='best')
        
        # Añadir información de correlación
        corr_text = f"Correlación de Pearson: {correlations['3d']['pearson']:.3f} (p={correlations['3d']['pearson_p']:.3f})\n"
        corr_text += f"Correlación de Spearman: {correlations['3d']['spearman']:.3f} (p={correlations['3d']['spearman_p']:.3f})"
        plt.annotate(
            corr_text, 
            xy=(0.05, 0.95), 
            xycoords='axes fraction', 
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8)
        )
        
        # Guardar gráfico
        plt.tight_layout()
        plt.savefig(os.path.join(self.correlation_dir, f"{symbol}_sentiment_price_scatter.png"), dpi=300)
        plt.close()
        
        # 2. Gráfico de barras: Cambio promedio de precio por nivel de sentimiento
        plt.figure(figsize=(14, 8))
        
        # Preparar datos para el gráfico
        sentiment_levels = []
        mean_changes_1d = []
        mean_changes_3d = []
        mean_changes_5d = []
        colors_list = []
        
        for level in ['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno']:
            if level in sentiment_stats:
                sentiment_levels.append(level)
                mean_changes_1d.append(sentiment_stats[level]['1d']['mean'])
                mean_changes_3d.append(sentiment_stats[level]['3d']['mean'])
                mean_changes_5d.append(sentiment_stats[level]['5d']['mean'])
                colors_list.append(self.colors[level])
        
        # Configurar posiciones de las barras
        x = np.arange(len(sentiment_levels))
        width = 0.25
        
        # Crear barras
        plt.bar(x - width, mean_changes_1d, width, label='1 Día', color=colors_list, alpha=0.7)
        plt.bar(x, mean_changes_3d, width, label='3 Días', color=colors_list, alpha=0.85)
        plt.bar(x + width, mean_changes_5d, width, label='5 Días', color=colors_list)
        
        # Añadir etiquetas y título
        plt.xlabel('Nivel de Sentimiento', fontsize=12)
        plt.ylabel('Cambio Promedio de Precio (%)', fontsize=12)
        plt.title(f'Cambio Promedio de Precio por Nivel de Sentimiento para {company_name} ({symbol})', fontsize=14)
        plt.xticks(x, ['Muy Negativo', 'Negativo', 'Neutro', 'Positivo', 'Muy Positivo'])
        plt.legend()
        
        # Añadir valores en las barras
        for i, v in enumerate(mean_changes_3d):
            plt.text(i, v + 0.5, f"{v:.2f}%", ha='center')
        
        # Guardar gráfico
        plt.tight_layout()
        plt.savefig(os.path.join(self.correlation_dir, f"{symbol}_sentiment_price_bars.png"), dpi=300)
        plt.close()
        
        # 3. Gráfico de líneas: Evolución del sentimiento y precio a lo largo del tiempo
        plt.figure(figsize=(14, 10))
        
        # Crear dos ejes y para diferentes escalas
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        # Graficar precio de cierre
        ax1.plot(df.index, df['close'], 'b-', linewidth=2, label='Precio de Cierre')
        ax1.set_xlabel('Fecha', fontsize=12)
        ax1.set_ylabel('Precio de Cierre ($)', color='b', fontsize=12)
        ax1.tick_params(axis='y', labelcolor='b')
        
        # Graficar sentimiento
        ax2.plot(df.index, df['combined_score'], 'r-', linewidth=2, label='Puntuación de Sentimiento')
        ax2.set_ylabel('Puntuación de Sentimiento', color='r', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='r')
        
        # Añadir título
        plt.title(f'Evolución del Precio y Sentimiento para {company_name} ({symbol})', fontsize=14)
        
        # Añadir leyendas
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # Guardar gráfico
        plt.tight_layout()
        plt.savefig(os.path.join(self.correlation_dir, f"{symbol}_sentiment_price_time.png"), dpi=300)
        plt.close()
    
    def _create_correlation_report(self, results, symbol, company_name):
        """
        Crea un informe de texto con los resultados de la correlación.
        
        Args:
            results (dict): Resultados del análisis de correlación.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
        """
        correlations = results['correlations']
        sentiment_stats = results['sentiment_stats']
        
        report = f"# Informe de Correlación entre Sentimiento y Precio para {company_name} ({symbol})\n\n"
        
        # Sección de correlaciones
        report += "## Correlaciones\n\n"
        report += "| Período | Correlación de Pearson | Valor p | Correlación de Spearman | Valor p |\n"
        report += "|---------|------------------------|---------|--------------------------|--------|\n"
        
        for days in ['1d', '3d', '5d']:
            pearson = correlations[days]['pearson']
            pearson_p = correlations[days]['pearson_p']
            spearman = correlations[days]['spearman']
            spearman_p = correlations[days]['spearman_p']
            
            report += f"| {days} | {pearson:.4f} | {pearson_p:.4f} | {spearman:.4f} | {spearman_p:.4f} |\n"
        
        # Sección de estadísticas por nivel de sentimiento
        report += "\n## Estadísticas por Nivel de Sentimiento\n\n"
        
        for level in ['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno']:
            if level in sentiment_stats:
                level_name = {
                    'muy_malo': 'Muy Negativo',
                    'malo': 'Negativo',
                    'neutro': 'Neutro',
                    'bueno': 'Positivo',
                    'muy_bueno': 'Muy Positivo'
                }[level]
                
                report += f"### {level_name}\n\n"
                report += "| Métrica | 1 Día | 3 Días | 5 Días |\n"
                report += "|---------|-------|--------|--------|\n"
                
                metrics = [
                    ('Cambio Promedio (%)', 'mean'),
                    ('Cambio Mediano (%)', 'median'),
                    ('Desviación Estándar (%)', 'std'),
                    ('Cambio Mínimo (%)', 'min'),
                    ('Cambio Máximo (%)', 'max'),
                    ('% de Cambios Positivos', 'positive_pct'),
                    ('Número de Observaciones', 'count')
                ]
                
                for metric_name, metric_key in metrics:
                    values = []
                    for days in ['1d', '3d', '5d']:
                        if days in sentiment_stats[level]:
                            value = sentiment_stats[level][days][metric_key]
                            if metric_key in ['mean', 'median', 'std', 'min', 'max', 'positive_pct']:
                                values.append(f"{value:.2f}")
                            else:
                                values.append(f"{value}")
                        else:
                            values.append("N/A")
                    
                    report += f"| {metric_name} | {values[0]} | {values[1]} | {values[2]} |\n"
                
                report += "\n"
        
        # Sección de interpretación
        report += "## Interpretación\n\n"
        
        # Evaluar la fuerza de la correlación
        strongest_corr = max([abs(correlations[days]['pearson']) for days in ['1d', '3d', '5d']])
        strongest_day = [days for days in ['1d', '3d', '5d'] 
                         if abs(correlations[days]['pearson']) == strongest_corr][0]
        
        if strongest_corr < 0.1:
            strength = "muy débil o inexistente"
        elif strongest_corr < 0.3:
            strength = "débil"
        elif strongest_corr < 0.5:
            strength = "moderada"
        elif strongest_corr < 0.7:
            strength = "fuerte"
        else:
            strength = "muy fuerte"
        
        # Determinar la dirección de la correlación
        direction = "positiva" if correlations[strongest_day]['pearson'] > 0 else "negativa"
        
        report += f"La correlación entre el sentimiento de las noticias y los cambios de precio para {company_name} es {strength} y {direction}. "
        report += f"La correlación más fuerte se observa en el período de {strongest_day}, "
        report += f"con un coeficiente de correlación de Pearson de {correlations[strongest_day]['pearson']:.4f}.\n\n"
        
        # Analizar la significancia estadística
        if correlations[strongest_day]['pearson_p'] < 0.05:
            report += "Esta correlación es estadísticamente significativa (p < 0.05), lo que sugiere que existe una relación real entre el sentimiento de las noticias y los movimientos de precios.\n\n"
        else:
            report += "Esta correlación no es estadísticamente significativa (p >= 0.05), lo que sugiere que la relación observada podría ser resultado del azar.\n\n"
        
        # Analizar los niveles de sentimiento
        best_level = None
        best_return = -float('inf')
        
        for level in ['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno']:
            if level in sentiment_stats and '3d' in sentiment_stats[level]:
                mean_return = sentiment_stats[level]['3d']['mean']
                if mean_return > best_return:
                    best_return = mean_return
                    best_level = level
        
        if best_level:
            level_name = {
                'muy_malo': 'Muy Negativo',
                'malo': 'Negativo',
                'neutro': 'Neutro',
                'bueno': 'Positivo',
                'muy_bueno': 'Muy Positivo'
            }[best_level]
            
            report += f"El nivel de sentimiento '{level_name}' está asociado con los mayores rendimientos positivos en un horizonte de 3 días, "
            report += f"con un cambio promedio de {sentiment_stats[best_level]['3d']['mean']:.2f}%.\n\n"
        
        # Conclusión
        report += "## Conclusión\n\n"
        
        if strongest_corr >= 0.3 and correlations[strongest_day]['pearson_p'] < 0.05:
            report += f"Existe evidencia de que el sentimiento de las noticias puede ser un indicador útil para predecir movimientos de precios para {company_name}. "
            report += "Los inversores podrían considerar incorporar el análisis de sentimiento en sus estrategias de inversión para esta acción.\n\n"
        else:
            report += f"La evidencia de una relación entre el sentimiento de las noticias y los movimientos de precios para {company_name} es limitada. "
            report += "Los inversores deberían ser cautelosos al utilizar el análisis de sentimiento como único indicador para esta acción y combinarlo con otros análisis.\n\n"
        
        # Guardar informe
        report_path = os.path.join(self.correlation_dir, f"{symbol}_correlation_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"Informe de correlación guardado en {report_path}")

if __name__ == "__main__":
    # Ruta al archivo de configuración
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'config.yaml'
    )
    
    # Crear instancia del correlador y analizar correlación
    correlator = SentimentPriceCorrelator(config_path)
    correlation_results = correlator.analyze_all_companies()
