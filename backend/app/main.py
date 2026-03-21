"""
FastAPI应用主入口
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 确保backend目录在路径中
backend_root = Path(__file__).parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1 import simulation, intelligence, entities, reports, websocket, demo
from app.config import settings
from app.db import init_db, close_db

# 配置日志
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.LOG_LEVEL,
    encoding="utf-8"
)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="地缘政治推演系统 API - 基于多Agent技术的战略推演平台",
    version="0.1.0",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(
    simulation.router,
    prefix="/api/v1/simulation",
    tags=["推演"]
)

app.include_router(
    intelligence.router,
    prefix="/api/v1/intelligence",
    tags=["情报收集"]
)

app.include_router(
    entities.router,
    prefix="/api/v1/entities",
    tags=["实体管理"]
)

app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["报告"]
)

# 注册WebSocket路由
app.include_router(
    websocket.router,
    prefix="/api/v1",
    tags=["WebSocket"]
)

# 注册演示场景路由
app.include_router(
    demo.router,
    prefix="/api/v1/demo",
    tags=["演示场景"]
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Tactiq System API",
        "version": "0.1.0",
        "description": "基于多Agent技术的地缘政治推演系统",
        "docs": "/docs",
        "endpoints": {
            "simulation": "/api/v1/simulation",
            "intelligence": "/api/v1/intelligence",
            "entities": "/api/v1/entities",
            "reports": "/api/v1/reports"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "version": "0.1.0"
    }


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # 开发环境下不阻断启动
        if settings.is_production:
            raise


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info(f"Shutting down {settings.APP_NAME}")
    
    # 关闭数据库连接
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development
    )
