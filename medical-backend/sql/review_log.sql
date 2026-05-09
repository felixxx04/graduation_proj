CREATE TABLE IF NOT EXISTS review_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    recommendation_id VARCHAR(32) NOT NULL,
    patient_id BIGINT,
    disease_cn VARCHAR(100) NOT NULL,
    disease_standardized VARCHAR(200),
    routing_path TEXT COMMENT 'L1-L2-L3 routing trace',
    system_drugs JSON COMMENT 'System recommended drugs',
    doctor_decision ENUM('confirm','modify','reject') NOT NULL,
    doctor_selected_drug VARCHAR(200),
    doctor_reason VARCHAR(500),
    doctor_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_recommendation_id (recommendation_id),
    INDEX idx_patient_id (patient_id),
    INDEX idx_decision (doctor_decision),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
