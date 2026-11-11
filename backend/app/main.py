"""ASGI application and static control room (frontend is isolated from backend source)."""
from contextlib import asynccontextmanager
from pathlib import Path
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import init_db

@asynccontextmanager
async def lifespan(_):
    if get_settings().app_env != 'production':
        init_db()
    yield

app = FastAPI(title='Falvorn WorldOps', version='0.2.0', lifespan=lifespan,
              description='Governed persistent multi-agent operations sandbox with human-approved external actions')
app.add_middleware(CORSMiddleware, allow_origins=get_settings().origins,
                   allow_credentials=False, allow_methods=['GET','POST'], allow_headers=['X-API-Key','Content-Type','Idempotency-Key'])
app.include_router(router)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Cache-Control'] = 'no-store'
    # No inline JavaScript in the control room. Docs Swagger UI is handled separately.
    if request.url.path == '/' or request.url.path.startswith('/assets/'):
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
    return response
FRONTEND = Path(os.environ.get('FRONTEND_DIR', str(Path(__file__).resolve().parents[2] / 'frontend')))
if FRONTEND.exists():
    app.mount('/assets', StaticFiles(directory=str(FRONTEND / 'src')), name='assets')
    @app.get('/', include_in_schema=False)
    def index():
        return FileResponse(FRONTEND / 'index.html')
