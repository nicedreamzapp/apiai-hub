import asyncio
import datetime
import subprocess
from config.settings import LOGS_DIR

async def run_command_async(job_name: str, command: str, group_name: str):
    """Run command asynchronously and log output"""
    log_file = LOGS_DIR / f"{job_name}.log"
    
    with open(log_file, "w") as log:
        log.write(f"=== {group_name} • {job_name} ===\n")
        log.write(f"Started: {datetime.datetime.now().isoformat()}\n")
        log.write(f"Command: {command}\n")
        log.write("=" * 50 + "\n\n")
        log.flush()
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True
            )
            
            async for line in process.stdout:
                decoded_line = line.decode('utf-8')
                log.write(decoded_line)
                log.flush()
            
            await process.wait()
            log.write(f"\n{'='*50}\n")
            log.write(f"Completed: {datetime.datetime.now().isoformat()}\n")
            log.write(f"Exit Code: {process.returncode}\n")
            log.write(f"Status: {'✅ SUCCESS' if process.returncode == 0 else '❌ FAILED'}\n")
            
        except Exception as e:
            log.write(f"\n❌ ERROR: {str(e)}\n")
            log.write(f"Failed: {datetime.datetime.now().isoformat()}\n")

def run_command_sync(command: str):
    """Run command synchronously"""
    proc = subprocess.run(["/bin/zsh", "-lc", command], capture_output=True, text=True, timeout=300)
    return {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr
    }
