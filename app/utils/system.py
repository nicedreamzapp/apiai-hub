import psutil
import datetime

def get_system_stats():
    """Get current system performance statistics"""
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    
    return {
        "cpu": f"{psutil.cpu_percent(interval=0.2):.1f}%",
        "memory": {
            "percent": f"{vm.percent:.1f}%",
            "used": f"{vm.used / (1024**3):.1f}GB",
            "total": f"{vm.total / (1024**3):.1f}GB"
        },
        "disk": {
            "percent": f"{du.percent:.1f}%",
            "free": f"{du.free / (1024**3):.1f}GB",
            "total": f"{du.total / (1024**3):.1f}GB"
        },
        "uptime_sec": int((datetime.datetime.now() - boot).total_seconds()),
    }
