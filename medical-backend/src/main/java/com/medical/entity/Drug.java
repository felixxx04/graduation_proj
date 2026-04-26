package com.medical.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class Drug {
    private Long id;
    private String drugCode;
    private String name;
    private String genericName;
    private String category;
    private String indications;
    private String contraindications;
    private String sideEffects;
    private String interactions;
    private String typicalDosage;
    private String typicalFrequency;
    private String description;
    private LocalDateTime createdAt;

    // v2: migration_v2.sql新增字段 (模型推理必需)
    private String pregnancyCategory;
    private String isOtc;
    private String drugClassEn;
    private String strength;
    private String dosageForm;
    private String atcCode;
    private String mechanismOfAction;
    private String routeOfAdministration;
}
