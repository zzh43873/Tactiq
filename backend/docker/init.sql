-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'UTC';

-- 创建日志表（可选，用于调试）
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
