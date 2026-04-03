package com.medical.entity;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class Recommendation {
    private Long id;
    private Long patientId;
    private Long userId;
    private String inputData;      // JSON
    private String resultData;     // JSON
    private Boolean dpEnabled;
    private BigDecimal epsilonUsed;
    private String recommendationType;  // realtime / batch
    private LocalDateTime createdAt;
}
