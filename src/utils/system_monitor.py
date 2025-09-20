"""
系統監控模組
提供系統效能監控和健康檢查功能
"""

import psutil
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from .enhanced_logging import log_operation, get_logger

logger = get_logger(__name__)

@dataclass
class SystemMetrics:
    """系統指標資料類別"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class ApplicationMetrics:
    """應用程式指標資料類別"""
    timestamp: datetime
    active_users: int
    total_subscriptions: int
    notifications_sent_today: int
    notifications_failed_today: int
    api_calls_today: int
    api_errors_today: int
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class SystemMonitor:
    """系統監控器"""
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.start_time = datetime.now()
        self.is_monitoring = False
        self.monitor_thread = None
        
        # 指標儲存
        self.system_metrics_history: List[SystemMetrics] = []
        self.app_metrics_history: List[ApplicationMetrics] = []
        self.max_history_size = 1440  # 24小時的分鐘數
        
        # 網路基準值
        self.network_baseline = self._get_network_baseline()
        
        # 應用程式計數器
        self.app_counters = {
            'notifications_sent_today': 0,
            'notifications_failed_today': 0,
            'api_calls_today': 0,
            'api_errors_today': 0,
            'active_users': 0,
            'total_subscriptions': 0
        }
        
        # 每日重置時間
        self.last_reset_date = datetime.now().date()
    
    def _get_network_baseline(self) -> Dict[str, float]:
        """取得網路使用基準值"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent / (1024 * 1024),  # MB
                'bytes_recv': net_io.bytes_recv / (1024 * 1024)   # MB
            }
        except Exception:
            return {'bytes_sent': 0.0, 'bytes_recv': 0.0}
    
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            logger.warning("監控已經在運行中")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        log_operation("系統監控啟動", {"interval": self.collection_interval})
    
    def stop_monitoring(self):
        """停止監控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        log_operation("系統監控停止")
    
    def _monitoring_loop(self):
        """監控循環"""
        while self.is_monitoring:
            try:
                # 收集系統指標
                system_metrics = self._collect_system_metrics()
                self.system_metrics_history.append(system_metrics)
                
                # 收集應用程式指標
                app_metrics = self._collect_app_metrics()
                self.app_metrics_history.append(app_metrics)
                
                # 限制歷史記錄大小
                if len(self.system_metrics_history) > self.max_history_size:
                    self.system_metrics_history.pop(0)
                
                if len(self.app_metrics_history) > self.max_history_size:
                    self.app_metrics_history.pop(0)
                
                # 檢查是否需要每日重置
                self._check_daily_reset()
                
                # 檢查警告條件
                self._check_alerts(system_metrics, app_metrics)
                
                # 儲存指標到檔案
                self._save_metrics_to_file()
                
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
            
            time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系統指標"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體使用情況
            memory = psutil.virtual_memory()
            
            # 磁碟使用情況
            disk = psutil.disk_usage('/')
            
            # 網路使用情況
            net_io = psutil.net_io_counters()
            network_sent = net_io.bytes_sent / (1024 * 1024) - self.network_baseline['bytes_sent']
            network_recv = net_io.bytes_recv / (1024 * 1024) - self.network_baseline['bytes_recv']
            
            # 程序數量
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_percent=disk.percent,
                disk_used_gb=disk.used / (1024 * 1024 * 1024),
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                network_sent_mb=max(0, network_sent),
                network_recv_mb=max(0, network_recv),
                process_count=process_count
            )
            
        except Exception as e:
            logger.error(f"收集系統指標時發生錯誤: {e}")
            # 返回預設值
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_percent=0.0,
                disk_used_gb=0.0,
                disk_free_gb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                process_count=0
            )
    
    def _collect_app_metrics(self) -> ApplicationMetrics:
        """收集應用程式指標"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ApplicationMetrics(
            timestamp=datetime.now(),
            active_users=self.app_counters['active_users'],
            total_subscriptions=self.app_counters['total_subscriptions'],
            notifications_sent_today=self.app_counters['notifications_sent_today'],
            notifications_failed_today=self.app_counters['notifications_failed_today'],
            api_calls_today=self.app_counters['api_calls_today'],
            api_errors_today=self.app_counters['api_errors_today'],
            uptime_seconds=uptime
        )
    
    def _check_daily_reset(self):
        """檢查是否需要每日重置計數器"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.app_counters.update({
                'notifications_sent_today': 0,
                'notifications_failed_today': 0,
                'api_calls_today': 0,
                'api_errors_today': 0
            })
            self.last_reset_date = current_date
            log_operation("每日計數器重置")
    
    def _check_alerts(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """檢查警告條件"""
        alerts = []
        
        # 系統資源警告
        if system_metrics.cpu_percent > 80:
            alerts.append(f"CPU使用率過高: {system_metrics.cpu_percent:.1f}%")
        
        if system_metrics.memory_percent > 85:
            alerts.append(f"記憶體使用率過高: {system_metrics.memory_percent:.1f}%")
        
        if system_metrics.disk_percent > 90:
            alerts.append(f"磁碟使用率過高: {system_metrics.disk_percent:.1f}%")
        
        # 應用程式警告
        if app_metrics.notifications_failed_today > 10:
            alerts.append(f"今日通知失敗次數過多: {app_metrics.notifications_failed_today}")
        
        if app_metrics.api_errors_today > 20:
            alerts.append(f"今日API錯誤次數過多: {app_metrics.api_errors_today}")
        
        # 記錄警告
        for alert in alerts:
            logger.warning(f"系統警告: {alert}")
    
    def _save_metrics_to_file(self):
        """儲存指標到檔案"""
        try:
            metrics_dir = Path("logs/metrics")
            metrics_dir.mkdir(parents=True, exist_ok=True)
            
            # 儲存最新的指標
            current_time = datetime.now()
            filename = f"metrics_{current_time.strftime('%Y%m%d')}.json"
            
            metrics_data = {
                'timestamp': current_time.isoformat(),
                'system_metrics': self.system_metrics_history[-1].to_dict() if self.system_metrics_history else None,
                'app_metrics': self.app_metrics_history[-1].to_dict() if self.app_metrics_history else None
            }
            
            with open(metrics_dir / filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metrics_data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"儲存指標到檔案時發生錯誤: {e}")
    
    def increment_counter(self, counter_name: str, amount: int = 1):
        """增加計數器"""
        if counter_name in self.app_counters:
            self.app_counters[counter_name] += amount
    
    def set_counter(self, counter_name: str, value: int):
        """設定計數器值"""
        if counter_name in self.app_counters:
            self.app_counters[counter_name] = value
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """取得當前指標"""
        return {
            'system': self.system_metrics_history[-1].to_dict() if self.system_metrics_history else None,
            'application': self.app_metrics_history[-1].to_dict() if self.app_metrics_history else None,
            'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600
        }
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """取得指標摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 過濾指定時間範圍內的指標
        recent_system = [m for m in self.system_metrics_history if m.timestamp >= cutoff_time]
        recent_app = [m for m in self.app_metrics_history if m.timestamp >= cutoff_time]
        
        summary = {
            'time_range_hours': hours,
            'data_points': len(recent_system),
            'system_summary': {},
            'application_summary': {}
        }
        
        if recent_system:
            summary['system_summary'] = {
                'avg_cpu_percent': sum(m.cpu_percent for m in recent_system) / len(recent_system),
                'max_cpu_percent': max(m.cpu_percent for m in recent_system),
                'avg_memory_percent': sum(m.memory_percent for m in recent_system) / len(recent_system),
                'max_memory_percent': max(m.memory_percent for m in recent_system),
                'avg_disk_percent': sum(m.disk_percent for m in recent_system) / len(recent_system)
            }
        
        if recent_app:
            summary['application_summary'] = {
                'total_notifications_sent': sum(m.notifications_sent_today for m in recent_app[-24:]),  # 最近24小時
                'total_notifications_failed': sum(m.notifications_failed_today for m in recent_app[-24:]),
                'total_api_calls': sum(m.api_calls_today for m in recent_app[-24:]),
                'total_api_errors': sum(m.api_errors_today for m in recent_app[-24:]),
                'current_active_users': recent_app[-1].active_users if recent_app else 0,
                'current_subscriptions': recent_app[-1].total_subscriptions if recent_app else 0
            }
        
        return summary
    
    def health_check(self) -> Dict[str, Any]:
        """系統健康檢查"""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # 檢查系統資源
            current_metrics = self.get_current_metrics()
            
            if current_metrics['system']:
                sys_metrics = current_metrics['system']
                
                # CPU 檢查
                if sys_metrics['cpu_percent'] > 90:
                    health_status['checks']['cpu'] = {'status': 'critical', 'value': sys_metrics['cpu_percent']}
                    health_status['status'] = 'critical'
                elif sys_metrics['cpu_percent'] > 70:
                    health_status['checks']['cpu'] = {'status': 'warning', 'value': sys_metrics['cpu_percent']}
                    if health_status['status'] == 'healthy':
                        health_status['status'] = 'warning'
                else:
                    health_status['checks']['cpu'] = {'status': 'healthy', 'value': sys_metrics['cpu_percent']}
                
                # 記憶體檢查
                if sys_metrics['memory_percent'] > 90:
                    health_status['checks']['memory'] = {'status': 'critical', 'value': sys_metrics['memory_percent']}
                    health_status['status'] = 'critical'
                elif sys_metrics['memory_percent'] > 80:
                    health_status['checks']['memory'] = {'status': 'warning', 'value': sys_metrics['memory_percent']}
                    if health_status['status'] == 'healthy':
                        health_status['status'] = 'warning'
                else:
                    health_status['checks']['memory'] = {'status': 'healthy', 'value': sys_metrics['memory_percent']}
                
                # 磁碟檢查
                if sys_metrics['disk_percent'] > 95:
                    health_status['checks']['disk'] = {'status': 'critical', 'value': sys_metrics['disk_percent']}
                    health_status['status'] = 'critical'
                elif sys_metrics['disk_percent'] > 85:
                    health_status['checks']['disk'] = {'status': 'warning', 'value': sys_metrics['disk_percent']}
                    if health_status['status'] == 'healthy':
                        health_status['status'] = 'warning'
                else:
                    health_status['checks']['disk'] = {'status': 'healthy', 'value': sys_metrics['disk_percent']}
            
            # 檢查應用程式狀態
            if current_metrics['application']:
                app_metrics = current_metrics['application']
                
                # 通知失敗率檢查
                total_notifications = app_metrics['notifications_sent_today'] + app_metrics['notifications_failed_today']
                if total_notifications > 0:
                    failure_rate = app_metrics['notifications_failed_today'] / total_notifications
                    if failure_rate > 0.1:  # 10% 失敗率
                        health_status['checks']['notifications'] = {'status': 'warning', 'failure_rate': failure_rate}
                        if health_status['status'] == 'healthy':
                            health_status['status'] = 'warning'
                    else:
                        health_status['checks']['notifications'] = {'status': 'healthy', 'failure_rate': failure_rate}
                
                # API 錯誤率檢查
                total_api_calls = app_metrics['api_calls_today'] + app_metrics['api_errors_today']
                if total_api_calls > 0:
                    error_rate = app_metrics['api_errors_today'] / total_api_calls
                    if error_rate > 0.05:  # 5% 錯誤率
                        health_status['checks']['api'] = {'status': 'warning', 'error_rate': error_rate}
                        if health_status['status'] == 'healthy':
                            health_status['status'] = 'warning'
                    else:
                        health_status['checks']['api'] = {'status': 'healthy', 'error_rate': error_rate}
            
        except Exception as e:
            health_status['status'] = 'error'
            health_status['error'] = str(e)
            logger.error(f"健康檢查時發生錯誤: {e}")
        
        return health_status

# 全域監控器實例
system_monitor = SystemMonitor()

# 便利函數
def start_monitoring():
    """啟動系統監控"""
    system_monitor.start_monitoring()

def stop_monitoring():
    """停止系統監控"""
    system_monitor.stop_monitoring()

def increment_counter(counter_name: str, amount: int = 1):
    """增加計數器"""
    system_monitor.increment_counter(counter_name, amount)

def set_counter(counter_name: str, value: int):
    """設定計數器"""
    system_monitor.set_counter(counter_name, value)

def get_current_metrics() -> Dict[str, Any]:
    """取得當前指標"""
    return system_monitor.get_current_metrics()

def get_metrics_summary(hours: int = 24) -> Dict[str, Any]:
    """取得指標摘要"""
    return system_monitor.get_metrics_summary(hours)

def health_check() -> Dict[str, Any]:
    """系統健康檢查"""
    return system_monitor.health_check()