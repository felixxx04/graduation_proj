package com.medical.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class Recommendation {
    private Long id;
    private Long patientId;
    private Long drugId;
    private String recommendation;
    private Double confidence;
    private LocalDateTime createdAt;
}
