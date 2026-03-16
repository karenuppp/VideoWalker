-- 创建摄像头表
CREATE TABLE IF NOT EXISTS cameras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    cms_url VARCHAR(255) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    location VARCHAR(100),
    stream_protocol VARCHAR(20) DEFAULT 'rtsp',
    scenes JSON,
    status VARCHAR(20) DEFAULT 'active',
    last_frame_time TIMESTAMP NULL,
    stream_url TEXT,
    stream_url_updated_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建抽帧记录表
CREATE TABLE IF NOT EXISTS frames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT NOT NULL,
    frame_path VARCHAR(255) NOT NULL,
    frame_time TIMESTAMP NOT NULL,
    ai_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建警告表
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    confidence DECIMAL(5,2),
    description TEXT,
    image_path VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'unread',
    detected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建场景模板表
CREATE TABLE IF NOT EXISTS scene_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scene_key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    detect_api VARCHAR(255) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建场景版本表
CREATE TABLE IF NOT EXISTS scene_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scene_template_id INT NOT NULL,
    version VARCHAR(32) NOT NULL,
    detector_type VARCHAR(20) NOT NULL DEFAULT 'yolo',
    model_name VARCHAR(128) NOT NULL,
    prompt TEXT NOT NULL,
    confidence_threshold FLOAT DEFAULT 0.7,
    params JSON,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (scene_template_id) REFERENCES scene_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建摄像头与场景绑定表
CREATE TABLE IF NOT EXISTS camera_scene_bindings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT NOT NULL,
    scene_version_id INT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    frame_interval_seconds INT NULL,
    confidence_threshold FLOAT NULL,
    model_name VARCHAR(128) NULL,
    last_run_at TIMESTAMP NULL,
    time_window_start VARCHAR(5) NULL,
    time_window_end VARCHAR(5) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
    FOREIGN KEY (scene_version_id) REFERENCES scene_versions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建识别结果表
CREATE TABLE IF NOT EXISTS detection_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT NOT NULL,
    frame_id INT NULL,
    binding_id INT NULL,
    scene_version_id INT NULL,
    scene_key VARCHAR(64) NOT NULL,
    detected BOOLEAN NOT NULL DEFAULT FALSE,
    confidence FLOAT NULL,
    description TEXT NULL,
    details JSON NULL,
    image_path VARCHAR(255) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
    FOREIGN KEY (frame_id) REFERENCES frames(id) ON DELETE SET NULL,
    FOREIGN KEY (binding_id) REFERENCES camera_scene_bindings(id) ON DELETE SET NULL,
    FOREIGN KEY (scene_version_id) REFERENCES scene_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建告警事件表
CREATE TABLE IF NOT EXISTS alert_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT NOT NULL,
    actor_user_id INT NULL,
    action VARCHAR(64) NOT NULL,
    from_status VARCHAR(20) NULL,
    to_status VARCHAR(20) NULL,
    note TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建通知日志表
CREATE TABLE IF NOT EXISTS notification_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT NOT NULL,
    channel VARCHAR(32) NOT NULL,
    recipient VARCHAR(128) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'sent',
    payload JSON NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建识别任务队列表
CREATE TABLE IF NOT EXISTS detection_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT NOT NULL,
    binding_id INT NOT NULL,
    scene_version_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    retries INT NOT NULL DEFAULT 0,
    error_message TEXT NULL,
    scheduled_for TIMESTAMP NOT NULL,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    frame_id INT NULL,
    detection_result_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
    FOREIGN KEY (binding_id) REFERENCES camera_scene_bindings(id) ON DELETE CASCADE,
    FOREIGN KEY (scene_version_id) REFERENCES scene_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (frame_id) REFERENCES frames(id) ON DELETE SET NULL,
    FOREIGN KEY (detection_result_id) REFERENCES detection_results(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建索引
CREATE INDEX idx_cameras_camera_id ON cameras(camera_id);

CREATE INDEX idx_alerts_camera_id ON alerts(camera_id);
CREATE INDEX idx_alerts_detected_at ON alerts(detected_at DESC);
CREATE INDEX idx_alerts_type ON alerts(alert_type);

CREATE INDEX idx_frames_camera_id ON frames(camera_id);
CREATE INDEX idx_frames_frame_time ON frames(frame_time DESC);

CREATE INDEX idx_scene_templates_key ON scene_templates(scene_key);
CREATE INDEX idx_scene_versions_template ON scene_versions(scene_template_id, is_published);
CREATE INDEX idx_camera_scene_bindings_camera ON camera_scene_bindings(camera_id, enabled);
CREATE INDEX idx_detection_results_camera_time ON detection_results(camera_id, detected_at DESC);
CREATE INDEX idx_detection_results_scene ON detection_results(scene_key, detected, detected_at DESC);
CREATE INDEX idx_alert_events_alert ON alert_events(alert_id, created_at DESC);
CREATE INDEX idx_notification_logs_alert ON notification_logs(alert_id, created_at DESC);
CREATE INDEX idx_detection_tasks_status_time ON detection_tasks(status, scheduled_for, id);
CREATE INDEX idx_detection_tasks_binding_status ON detection_tasks(binding_id, status, scheduled_for);
