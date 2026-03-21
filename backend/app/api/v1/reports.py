"""
报告API路由
"""

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.get("/simulation/{simulation_id}")
async def generate_simulation_report(simulation_id: str):
    """生成推演报告"""
    # TODO: 实现报告生成
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/simulation/{simulation_id}/export")
async def export_simulation_report(
    simulation_id: str,
    format: str = "pdf"  # pdf, docx, markdown
):
    """导出推演报告"""
    # TODO: 实现报告导出
    raise HTTPException(status_code=501, detail="Not implemented")
