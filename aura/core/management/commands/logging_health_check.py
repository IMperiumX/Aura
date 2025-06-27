import json
import logging
import time
from collections import defaultdict
from typing import Dict, Any

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger('aura.management')


class Command(BaseCommand):
    """
    Comprehensive logging health check and diagnostics command.

    This command provides:
    - Logging system health verification
    - Performance metrics analysis
    - Error rate monitoring
    - Handler status checks
    - Configuration validation
    - Recommendations for optimization
    """

    help = 'Perform comprehensive logging system health checks and diagnostics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['json', 'table', 'summary'],
            default='table',
            help='Output format for the health check report'
        )
        parser.add_argument(
            '--check-handlers',
            action='store_true',
            help='Perform detailed handler health checks'
        )
        parser.add_argument(
            '--metrics-window',
            type=int,
            default=3600,
            help='Time window in seconds for metrics analysis (default: 1 hour)'
        )
        parser.add_argument(
            '--alert-thresholds',
            action='store_true',
            help='Check if any alert thresholds have been exceeded'
        )

    def handle(self, *args, **options):
        """
        Main command handler that orchestrates all health checks.
        """
        self.stdout.write(
            self.style.SUCCESS('🔍 Starting Aura Logging System Health Check...\n')
        )

        # Collect all health data
        health_data = {
            'timestamp': time.time(),
            'system_info': self._get_system_info(),
            'logging_config': self._check_logging_config(),
            'handler_health': self._check_handler_health() if options['check_handlers'] else {},
            'metrics_analysis': self._analyze_metrics(options['metrics_window']),
            'alert_status': self._check_alert_thresholds() if options['alert_thresholds'] else {},
            'recommendations': [],
        }

        # Generate recommendations
        health_data['recommendations'] = self._generate_recommendations(health_data)

        # Output results
        self._output_results(health_data, options['format'])

        # Determine exit code based on health status
        if self._has_critical_issues(health_data):
            self.stdout.write(
                self.style.ERROR('\n❌ Critical issues detected in logging system!')
            )
            exit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Logging system health check completed successfully!')
            )

    def _get_system_info(self) -> Dict[str, Any]:
        """
        Gather basic system information.
        """
        import platform
        import sys

        try:
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_count = psutil.cpu_count()
        except ImportError:
            memory = disk = None
            cpu_count = 'unknown'

        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
            'environment': getattr(settings, 'ENVIRONMENT', 'unknown'),
            'service_name': getattr(settings, 'SERVICE_NAME', 'unknown'),
            'version': getattr(settings, 'VERSION', 'unknown'),
            'cpu_count': cpu_count,
            'memory_total': memory.total if memory else 'unknown',
            'memory_available': memory.available if memory else 'unknown',
            'disk_total': disk.total if disk else 'unknown',
            'disk_free': disk.free if disk else 'unknown',
        }

    def _check_logging_config(self) -> Dict[str, Any]:
        """
        Validate logging configuration.
        """
        config_status = {
            'valid': True,
            'issues': [],
            'handlers_configured': 0,
            'loggers_configured': 0,
            'filters_configured': 0,
            'formatters_configured': 0,
        }

        try:
            logging_config = settings.LOGGING

            # Count configured components
            config_status['handlers_configured'] = len(logging_config.get('handlers', {}))
            config_status['loggers_configured'] = len(logging_config.get('loggers', {}))
            config_status['filters_configured'] = len(logging_config.get('filters', {}))
            config_status['formatters_configured'] = len(logging_config.get('formatters', {}))

            # Check for required components
            required_handlers = ['console', 'json']
            for handler in required_handlers:
                if handler not in logging_config.get('handlers', {}):
                    config_status['issues'].append(f"Missing required handler: {handler}")
                    config_status['valid'] = False

            # Check for advanced filters
            advanced_filters = ['request_context', 'security', 'sampling']
            for filter_name in advanced_filters:
                if filter_name not in logging_config.get('filters', {}):
                    config_status['issues'].append(f"Missing advanced filter: {filter_name}")

            # Validate handler configurations
            for name, handler_config in logging_config.get('handlers', {}).items():
                if 'class' not in handler_config:
                    config_status['issues'].append(f"Handler {name} missing class specification")
                    config_status['valid'] = False

        except Exception as e:
            config_status['valid'] = False
            config_status['issues'].append(f"Error reading logging configuration: {str(e)}")

        return config_status

    def _check_handler_health(self) -> Dict[str, Any]:
        """
        Check the health of individual logging handlers.
        """
        handler_health = {}

        # Get all configured handlers
        root_logger = logging.getLogger()

        for handler in root_logger.handlers:
            handler_name = handler.__class__.__name__
            health_info = {
                'class': handler_name,
                'level': handler.level,
                'formatter': handler.formatter.__class__.__name__ if handler.formatter else None,
                'filters': [f.__class__.__name__ for f in handler.filters],
                'healthy': True,
                'issues': [],
            }

            # Check for custom handler health stats
            if hasattr(handler, 'get_health_stats'):
                try:
                    stats = handler.get_health_stats()
                    health_info['stats'] = stats

                    # Check for concerning stats
                    if stats.get('circuit_open', False):
                        health_info['healthy'] = False
                        health_info['issues'].append("Circuit breaker is open")

                    if stats.get('records_dropped', 0) > 0:
                        health_info['issues'].append(
                            f"Records dropped: {stats['records_dropped']}"
                        )

                    error_rate = (stats.get('error_count', 0) /
                                max(1, stats.get('records_processed', 1)))
                    if error_rate > 0.1:
                        health_info['issues'].append(
                            f"High error rate: {error_rate:.1%}"
                        )

                except Exception as e:
                    health_info['issues'].append(f"Error getting handler stats: {str(e)}")

            handler_health[handler_name] = health_info

        return handler_health

    def _analyze_metrics(self, window_seconds: int) -> Dict[str, Any]:
        """
        Analyze performance and logging metrics from the specified time window.
        """
        current_time = int(time.time())
        start_time = current_time - window_seconds

        metrics = {
            'window_seconds': window_seconds,
            'log_levels': defaultdict(int),
            'error_rate': 0,
            'performance_stats': {},
            'security_events': 0,
            'top_loggers': {},
        }

        try:
            # Analyze log level metrics
            for level in ['critical', 'error', 'warning', 'info', 'debug']:
                pattern = f"metrics:log_level_{level}"
                level_data = cache.get(pattern, {})

                for timestamp, count in level_data.items():
                    if int(timestamp) >= start_time:
                        metrics['log_levels'][level] += count

            # Calculate error rate
            total_logs = sum(metrics['log_levels'].values())
            error_logs = metrics['log_levels']['error'] + metrics['log_levels']['critical']
            if total_logs > 0:
                metrics['error_rate'] = error_logs / total_logs

            # Analyze performance metrics
            perf_metrics = ['response_time', 'db_queries', 'memory_delta']
            for metric in perf_metrics:
                pattern = f"metrics:perf_{metric}"
                metric_data = cache.get(pattern, {})

                values = [
                    value for timestamp, value in metric_data.items()
                    if int(timestamp) >= start_time
                ]

                if values:
                    metrics['performance_stats'][metric] = {
                        'avg': sum(values) / len(values),
                        'max': max(values),
                        'min': min(values),
                        'count': len(values),
                    }

            # Check security events
            security_data = cache.get("metrics:security_events", {})
            for timestamp, count in security_data.items():
                if int(timestamp) >= start_time:
                    metrics['security_events'] += count

        except Exception as e:
            metrics['error'] = f"Error analyzing metrics: {str(e)}"

        return metrics

    def _check_alert_thresholds(self) -> Dict[str, Any]:
        """
        Check if any alert thresholds have been exceeded.
        """
        alerts = {
            'active_alerts': [],
            'threshold_checks': {},
        }

        try:
            # Check for active alerts in cache
            alert_keys = cache.keys("alert:*")
            for key in alert_keys:
                alert_data = cache.get(key)
                if alert_data:
                    alerts['active_alerts'].append(alert_data)

            # Check current metrics against thresholds
            thresholds = {
                'error_rate': 0.05,  # 5% error rate
                'slow_request_rate': 0.1,  # 10% slow requests
                'memory_usage': 0.8,  # 80% memory usage
            }

            for threshold_name, threshold_value in thresholds.items():
                # Implementation would check current metrics
                alerts['threshold_checks'][threshold_name] = {
                    'threshold': threshold_value,
                    'current_value': 0,  # Would be calculated from metrics
                    'exceeded': False,
                }

        except Exception as e:
            alerts['error'] = f"Error checking alert thresholds: {str(e)}"

        return alerts

    def _generate_recommendations(self, health_data: Dict[str, Any]) -> list:
        """
        Generate optimization recommendations based on health data.
        """
        recommendations = []

        # Configuration recommendations
        config = health_data.get('logging_config', {})
        if config.get('issues'):
            recommendations.append({
                'category': 'configuration',
                'priority': 'high',
                'title': 'Logging Configuration Issues',
                'description': 'Fix logging configuration issues to ensure proper operation',
                'actions': config['issues'],
            })

        # Performance recommendations
        metrics = health_data.get('metrics_analysis', {})
        if metrics.get('error_rate', 0) > 0.05:
            recommendations.append({
                'category': 'performance',
                'priority': 'medium',
                'title': 'High Error Rate',
                'description': f"Error rate is {metrics['error_rate']:.1%}, consider investigating root causes",
                'actions': ['Review error logs', 'Check application health', 'Monitor trends'],
            })

        # Handler health recommendations
        handler_health = health_data.get('handler_health', {})
        for handler_name, health_info in handler_health.items():
            if not health_info.get('healthy', True):
                recommendations.append({
                    'category': 'handlers',
                    'priority': 'high',
                    'title': f'Handler Issues: {handler_name}',
                    'description': f"Handler {handler_name} has health issues",
                    'actions': health_info.get('issues', []),
                })

        # Security recommendations
        if metrics.get('security_events', 0) > 0:
            recommendations.append({
                'category': 'security',
                'priority': 'high',
                'title': 'Security Events Detected',
                'description': f"Detected {metrics['security_events']} security events",
                'actions': ['Review security logs', 'Check for threats', 'Update security policies'],
            })

        return recommendations

    def _has_critical_issues(self, health_data: Dict[str, Any]) -> bool:
        """
        Determine if there are any critical issues that require immediate attention.
        """
        # Check for high-priority recommendations
        recommendations = health_data.get('recommendations', [])
        for rec in recommendations:
            if rec.get('priority') == 'high':
                return True

        # Check configuration validity
        if not health_data.get('logging_config', {}).get('valid', True):
            return True

        # Check handler health
        handler_health = health_data.get('handler_health', {})
        for health_info in handler_health.values():
            if not health_info.get('healthy', True):
                return True

        return False

    def _output_results(self, health_data: Dict[str, Any], format_type: str) -> None:
        """
        Output health check results in the specified format.
        """
        if format_type == 'json':
            self.stdout.write(json.dumps(health_data, indent=2, default=str))
        elif format_type == 'summary':
            self._output_summary(health_data)
        else:  # table format
            self._output_table(health_data)

    def _output_summary(self, health_data: Dict[str, Any]) -> None:
        """
        Output a concise summary of the health check.
        """
        self.stdout.write(self.style.HTTP_INFO('📊 LOGGING SYSTEM HEALTH SUMMARY'))
        self.stdout.write('=' * 50)

        # System info
        system = health_data['system_info']
        self.stdout.write(f"Environment: {system.get('environment', 'unknown')}")
        self.stdout.write(f"Service: {system.get('service_name', 'unknown')} v{system.get('version', 'unknown')}")

        # Configuration status
        config = health_data['logging_config']
        status_icon = '✅' if config.get('valid') else '❌'
        self.stdout.write(f"\nConfiguration: {status_icon} {'Valid' if config.get('valid') else 'Invalid'}")

        # Metrics summary
        metrics = health_data['metrics_analysis']
        self.stdout.write(f"\nMetrics Window: {metrics.get('window_seconds', 0)} seconds")
        self.stdout.write(f"Error Rate: {metrics.get('error_rate', 0):.1%}")
        self.stdout.write(f"Security Events: {metrics.get('security_events', 0)}")

        # Recommendations
        recommendations = health_data['recommendations']
        if recommendations:
            self.stdout.write(f"\n⚠️  {len(recommendations)} recommendations:")
            for rec in recommendations[:3]:  # Show top 3
                priority_color = self.style.ERROR if rec['priority'] == 'high' else self.style.WARNING
                self.stdout.write(f"  {priority_color(rec['title'])}")

    def _output_table(self, health_data: Dict[str, Any]) -> None:
        """
        Output detailed health check results in table format.
        """
        # System Information
        self.stdout.write(self.style.HTTP_INFO('🖥️  SYSTEM INFORMATION'))
        self.stdout.write('-' * 40)
        system = health_data['system_info']
        for key, value in system.items():
            if key in ['environment', 'service_name', 'version', 'platform']:
                self.stdout.write(f"{key.replace('_', ' ').title()}: {value}")

        # Configuration Status
        self.stdout.write(f"\n{self.style.HTTP_INFO('⚙️  CONFIGURATION STATUS')}")
        self.stdout.write('-' * 40)
        config = health_data['logging_config']
        status_icon = '✅' if config.get('valid') else '❌'
        self.stdout.write(f"Status: {status_icon} {'Valid' if config.get('valid') else 'Invalid'}")
        self.stdout.write(f"Handlers: {config.get('handlers_configured', 0)}")
        self.stdout.write(f"Loggers: {config.get('loggers_configured', 0)}")
        self.stdout.write(f"Filters: {config.get('filters_configured', 0)}")

        if config.get('issues'):
            self.stdout.write(f"\n{self.style.ERROR('Issues:')}")
            for issue in config['issues']:
                self.stdout.write(f"  • {issue}")

        # Metrics Analysis
        self.stdout.write(f"\n{self.style.HTTP_INFO('📈 METRICS ANALYSIS')}")
        self.stdout.write('-' * 40)
        metrics = health_data['metrics_analysis']

        if 'log_levels' in metrics:
            self.stdout.write("Log Levels:")
            for level, count in metrics['log_levels'].items():
                if count > 0:
                    self.stdout.write(f"  {level.upper()}: {count}")

        if metrics.get('error_rate') is not None:
            error_color = self.style.ERROR if metrics['error_rate'] > 0.05 else self.style.SUCCESS
            self.stdout.write(f"Error Rate: {error_color(f'{metrics[\"error_rate\"]:.1%}')}")

        # Recommendations
        recommendations = health_data['recommendations']
        if recommendations:
            self.stdout.write(f"\n{self.style.HTTP_INFO('💡 RECOMMENDATIONS')}")
            self.stdout.write('-' * 40)
            for i, rec in enumerate(recommendations, 1):
                priority_color = (self.style.ERROR if rec['priority'] == 'high'
                                else self.style.WARNING if rec['priority'] == 'medium'
                                else self.style.SUCCESS)

                self.stdout.write(f"{i}. {priority_color(rec['title'])} [{rec['priority'].upper()}]")
                self.stdout.write(f"   {rec['description']}")
                if rec.get('actions'):
                    for action in rec['actions'][:2]:  # Show first 2 actions
                        self.stdout.write(f"   • {action}")
                self.stdout.write("")
