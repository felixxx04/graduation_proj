package com.medical.dto.request;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class ClinicalMetricsRequest {
    private String renalFunction;
    private String hepaticFunction;
    private String smokingStatus;
    private String drinkingStatus;
    private Integer bloodPressureSystolic;
    private Integer bloodPressureDiastolic;
    private BigDecimal fastingGlucose;
    private BigDecimal hba1c;
    private BigDecimal cholesterolTotal;
    private BigDecimal cholesterolLdl;
    private Integer heartRate;
}
