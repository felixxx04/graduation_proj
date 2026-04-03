package com.medical.dto.request;

import lombok.Data;
import java.util.List;

/**
 * 患者创建/更新请求DTO
 */
@Data
public class PatientRequest {
    private String name;
    private String gender;  // "MALE"/"FEMALE"/"UNKNOWN"
    private Integer age;
    private String phone;

    // 健康档案字段
    private Double height;
    private Double weight;
    private String bloodType;
    private List<String> allergies;
    private List<String> chronicDiseases;
    private List<String> currentMedications;
    private String medicalHistory;
    private String symptoms;
}
