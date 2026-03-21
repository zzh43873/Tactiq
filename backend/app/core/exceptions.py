"""
自定义异常
"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """应用基础异常"""
    
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(AppException):
    """资源不存在异常"""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(AppException):
    """请求参数错误异常"""
    
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(AppException):
    """未授权异常"""
    
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(AppException):
    """禁止访问异常"""
    
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationException(AppException):
    """数据验证异常"""
    
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class SimulationException(AppException):
    """推演异常"""
    
    def __init__(self, detail: str = "Simulation failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
