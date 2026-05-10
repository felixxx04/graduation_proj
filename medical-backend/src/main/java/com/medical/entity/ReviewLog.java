package com.medical.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ReviewLog {
    private Long id;
    private String recommendationId;
    private Long patientId;
    private String diseaseCn;
    private String diseaseStandardized;
    private String routingPath;
    private String systemDrugs;
    private String doctorDecision;
    private String doctorSelectedDrug;
    private String doctorReason;
    private String treatmentAdvice;
    private String treatmentTemplate;
    private Long doctorId;
    private LocalDateTime createdAt;
}
