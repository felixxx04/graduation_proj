package com.medical.entity;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class PrivacyConfig {
    private Long id;
    private Long userId;
    private BigDecimal epsilon;
    private BigDecimal delta;
    private BigDecimal sensitivity;
    private String noiseMechanism;
    private String applicationStage;
    private BigDecimal privacyBudget;
    private BigDecimal budgetUsed;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
