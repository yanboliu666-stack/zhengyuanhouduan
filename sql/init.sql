-- 创建 PostgreSQL 数据库表结构

-- 1. 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
                                        id          BIGSERIAL PRIMARY KEY,
                                        username    VARCHAR(50) NOT NULL UNIQUE,
    password    VARCHAR(100) NOT NULL,
    role        VARCHAR(20) NOT NULL DEFAULT 'OPERATOR',
    status      VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 初始化默认管理员 (密码: admin123)
INSERT INTO sys_user (username, password, role, status)
VALUES ('admin', '$2a$10$7R0wM8JzDkI8uE9F/Y3x2e0.kR4N9HwYq2U8I8O0P1Q2R3S4T5U6V', 'ADMIN', 'ACTIVE')
    ON CONFLICT (username) DO NOTHING;

-- 2. 路口信息表
CREATE TABLE IF NOT EXISTS intersection (
                                            id              VARCHAR(32) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    longitude       NUMERIC(10, 7),
    latitude        NUMERIC(10, 7),
    road_type       VARCHAR(20) DEFAULT 'CROSS',
    control_mode    VARCHAR(20) DEFAULT 'WEBSTER',
    status          VARCHAR(10) DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 3. 车道表
CREATE TABLE IF NOT EXISTS lane (
                                    id              VARCHAR(32) PRIMARY KEY,
    intersection_id VARCHAR(32) NOT NULL,
    lane_code       VARCHAR(10) NOT NULL,
    direction       VARCHAR(10) NOT NULL,
    roi_polygon     TEXT,
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 4. 设备表
CREATE TABLE IF NOT EXISTS device (
                                      id              VARCHAR(32) PRIMARY KEY,
    intersection_id VARCHAR(32) NOT NULL,
    device_type     VARCHAR(20) NOT NULL,
    ip_address      VARCHAR(45),
    status          VARCHAR(10) DEFAULT 'ONLINE',
    last_heartbeat  TIMESTAMP,
    firmware_ver    VARCHAR(20),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 5. 配时方案记录表
CREATE TABLE IF NOT EXISTS timing_plan (
                                           id              BIGSERIAL PRIMARY KEY,
                                           intersection_id VARCHAR(32) NOT NULL,
    cycle_length    INT NOT NULL,
    strategy        VARCHAR(20) NOT NULL,
    phases_json     TEXT NOT NULL,
    status          VARCHAR(10) DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 6. 告警记录表
CREATE TABLE IF NOT EXISTS alert (
                                     id              BIGSERIAL PRIMARY KEY,
                                     intersection_id VARCHAR(32),
    device_id       VARCHAR(32),
    alert_type      VARCHAR(30) NOT NULL,
    severity        VARCHAR(10) DEFAULT 'WARNING',
    message         TEXT,
    resolved        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );