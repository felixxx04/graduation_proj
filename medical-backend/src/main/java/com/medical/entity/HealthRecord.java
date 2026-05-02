package com.medical.entity;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 患者健康档案实体
 */
@Data
public class HealthRecord {
    private Long id;
    private Long patientId;
    private LocalDate recordDate;
    private Integer age;
    private BigDecimal height;
    private BigDecimal weight;
    private String bloodType;
    private String chronicDiseases;    // JSON存储
    private String allergies;          // JSON存储
    private String currentMedications; // JSON存储
    private String medicalHistory;
    private String symptoms;
    private Boolean isLatest;
    private LocalDateTime createdAt;

    // v2: migration_v2.sql新增字段 (模型推理必需)
    private String smokingStatus;      // ENUM: never/former/current/unknown
    private String drinkingStatus;     // ENUM: none/occasional/regular/heavy/unknown
    private String renalFunction;      // ENUM: normal/mild_impairment/moderate_impairment/severe_impairment/unknown
    private String hepaticFunction;    // ENUM: normal/mild_impairment/moderate_impairment/severe_impairment/unknown
    private Integer bloodPressureSystolic;   // 收缩压(mmHg)
    private Integer bloodPressureDiastolic;  // 舒张压(mmHg)
    private BigDecimal fastingGlucose;       // 空腹血糖(mmol/L)
    private BigDecimal hba1c;               // 糖化血红蛋白(%)
    private BigDecimal cholesterolTotal;     // 总胆固醇(mmol/L)
    private BigDecimal cholesterolLdl;       // LDL胆固醇(mmol/L)
    private Integer heartRate;              // 心率(bpm)
}