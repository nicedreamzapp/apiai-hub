from fastapi import Header, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel
from config.auth import guard
from jobs.definitions import JOBS
from jobs.executor import run_command_async, run_command_sync

class RunReq(BaseModel):
    job_name: str

def create_job_routes(app):
    @app.get("/jobs")
    def list_jobs(request: Request, x_api_key: str | None = Header(None)):
        guard(x_api_key, request)
        return JOBS

    @app.post("/run")
    async def run_job_async(req: RunReq, background_tasks: BackgroundTasks, request: Request, x_api_key: str | None = Header(None)):
        guard(x_api_key, request)
        
        # Find job in any group
        job_info = None
        group_name = None
        for group, group_data in JOBS.items():
            if req.job_name in group_data["jobs"]:
                job_info = group_data["jobs"][req.job_name]
                group_name = group
                break
        
        if not job_info:
            raise HTTPException(status_code=404, detail=f"Job '{req.job_name}' not found")
        
        background_tasks.add_task(run_command_async, req.job_name, job_info["cmd"], group_name)
        
        return {
            "status": "started",
            "job_name": req.job_name,
            "group": group_name,
            "message": f"Job '{job_info['name']}' started successfully"
        }

    @app.post("/run_sync")
    def run_sync(req: RunReq, request: Request, x_api_key: str | None = Header(None)):
        guard(x_api_key, request)
        
        # Find job in any group
        job_info = None
        for group_data in JOBS.values():
            if req.job_name in group_data["jobs"]:
                job_info = group_data["jobs"][req.job_name]
                break
                
        if not job_info:
            raise HTTPException(status_code=404, detail=f"Job '{req.job_name}' not found")
        
        result = run_command_sync(job_info["cmd"])
        result["job_name"] = req.job_name
        return result
