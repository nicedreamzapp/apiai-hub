from fastapi import Header, Request
from config.auth import guard
from config.settings import LOGS_DIR

def create_log_routes(app):
    @app.get("/logs/{job_name}")
    def get_logs(job_name: str, request: Request, x_api_key: str | None = Header(None)):
        guard(x_api_key, request)
        
        log_file = LOGS_DIR / f"{job_name}.log"
        if not log_file.exists():
            return {"error": f"No log file found for job '{job_name}'"}
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Return last 200 lines
                tail_lines = lines[-200:] if len(lines) > 200 else lines
                return {
                    "job_name": job_name,
                    "log_content": ''.join(tail_lines),
                    "total_lines": len(lines)
                }
        except Exception as e:
            return {"error": f"Could not read log file: {str(e)}"}
