package com.medical.dto.request;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class PrivacyConfigRequest {
    private BigDecimal epsilon;
    private BigDecimal delta;
    private BigDecimal sensitivity;
    private String noiseMechanism;
    private String applicationStage;
    private BigDecimal privacyBudget;
}
