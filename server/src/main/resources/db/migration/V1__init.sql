CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE patients (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(16) NOT NULL,
    height DOUBLE NOT NULL,
    weight DOUBLE NOT NULL,
    medical_history TEXT NULL,
    created_by BIGINT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_patients_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE patient_allergies (
    patient_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_patient_allergies_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE patient_diseases (
    patient_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_patient_diseases_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE patient_medications (
    patient_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_patient_medications_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE privacy_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    epsilon DOUBLE NOT NULL,
    delta_value DOUBLE NOT NULL,
    sensitivity DOUBLE NOT NULL,
    noise_mechanism VARCHAR(16) NOT NULL,
    application_stage VARCHAR(16) NOT NULL,
    privacy_budget DOUBLE NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE privacy_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    type VARCHAR(32) NOT NULL,
    epsilon_spent DOUBLE NOT NULL,
    delta_spent DOUBLE NULL,
    note TEXT NULL,
    created_by BIGINT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_privacy_events_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE drugs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    typical_dosage VARCHAR(64) NOT NULL,
    typical_frequency VARCHAR(128) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE drug_indications (
    drug_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_drug_indications_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);

CREATE TABLE drug_contraindications (
    drug_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_drug_contraindications_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);

CREATE TABLE drug_side_effects (
    drug_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_drug_side_effects_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);

CREATE TABLE drug_interactions (
    drug_id BIGINT NOT NULL,
    item VARCHAR(128) NOT NULL,
    CONSTRAINT fk_drug_interactions_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);

CREATE TABLE recommendations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_id BIGINT NULL,
    created_by BIGINT NULL,
    age INT NULL,
    gender VARCHAR(16) NULL,
    diseases TEXT NULL,
    symptoms TEXT NULL,
    allergies TEXT NULL,
    current_medications TEXT NULL,
    dp_enabled BIT NOT NULL,
    epsilon_used DOUBLE NULL,
    noise_mechanism VARCHAR(16) NULL,
    application_stage VARCHAR(16) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_recommendation_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
    CONSTRAINT fk_recommendation_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE recommendation_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    recommendation_id BIGINT NOT NULL,
    drug_id BIGINT NOT NULL,
    rank_index INT NOT NULL,
    score DOUBLE NOT NULL,
    confidence DOUBLE NOT NULL,
    dp_noise DOUBLE NULL,
    reason TEXT NULL,
    interactions TEXT NULL,
    side_effects TEXT NULL,
    warnings TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_recommendation_items_rec FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE CASCADE,
    CONSTRAINT fk_recommendation_items_drug FOREIGN KEY (drug_id) REFERENCES drugs(id)
);

CREATE TABLE training_runs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    created_by BIGINT NULL,
    status VARCHAR(16) NOT NULL,
    total_epochs INT NOT NULL,
    epsilon_per_epoch DOUBLE NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_training_runs_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE training_epochs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    training_run_id BIGINT NOT NULL,
    epoch_index INT NOT NULL,
    loss DOUBLE NOT NULL,
    accuracy DOUBLE NOT NULL,
    epsilon_spent DOUBLE NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_training_epochs_run FOREIGN KEY (training_run_id) REFERENCES training_runs(id) ON DELETE CASCADE
);

CREATE TABLE audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    actor_id BIGINT NULL,
    action VARCHAR(64) NOT NULL,
    target_type VARCHAR(64) NULL,
    target_id BIGINT NULL,
    detail TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_id) REFERENCES users(id)
);
