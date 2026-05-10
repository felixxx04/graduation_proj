package com.medical.dto.response;

import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class RecommendationHistoryItem {
    private Long id;
    private Long patientId;
    private List<String> recommendedDrugs;
    private String primaryDisease;
    private Boolean dpEnabled;
    private Double epsilonUsed;
    private String reviewStatus;
    private LocalDateTime createdAt;
}
