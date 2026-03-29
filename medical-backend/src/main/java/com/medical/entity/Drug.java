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
}
