package com.medical.dto.response;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 患者完整信息DTO，合并 patient 和 patient_health_record 表数据
 */
@Data
public class PatientProfile {
    // 来自 patient 表
    private Long id;
    private String name;
    private String gender;  // "MALE"/"FEMALE"/"UNKNOWN"
    private LocalDate birthDate;
    private String phone;

    // 来自 patient_health_record 表
    private Integer age;
    private Double height;
    private Double weight;
    private String bloodType;
    private List<String> allergies;
    private List<String> chronicDiseases;
    private List<String> currentMedications;
    private String medicalHistory;
    private String symptoms;

    // 元数据
    private LocalDateTime createdAt;
}
