from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import sync as sync_router
from app.routers import produzione as produzione_router
from app.routers import articoli as articoli_router
from app.routers import reparto as reparto_router
from app.routers import magazzino as magazzino_router
from app.routers import logistica as logistica_router
from app.routers import eventi as eventi_router
from app.routers import auth as auth_router
from app.sync.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MRS V1 avvio — starting scheduler")
    start_scheduler()
    yield
    logger.info("MRS V1 shutdown — stopping scheduler")
    stop_scheduler()


app = FastAPI(
    title="MRS — Manufacturing Resource System",
    version="1.0.0",
    description="Backend API per MRS V1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringere in produzione
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_router.router)
app.include_router(produzione_router.router)
app.include_router(articoli_router.router)
app.include_router(reparto_router.router)
app.include_router(magazzino_router.router)
app.include_router(logistica_router.router)
app.include_router(eventi_router.router)
app.include_router(auth_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
