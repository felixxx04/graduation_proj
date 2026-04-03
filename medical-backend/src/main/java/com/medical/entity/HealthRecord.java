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
}
