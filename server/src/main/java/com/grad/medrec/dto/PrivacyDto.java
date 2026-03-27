package com.grad.medrec.dto;

import com.grad.medrec.enumtype.ApplicationStage;
import com.grad.medrec.enumtype.NoiseMechanism;
import com.grad.medrec.enumtype.PrivacyEventType;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;
import java.util.List;

public final class PrivacyDto {

    private PrivacyDto() {
    }

    public record ConfigRequest(
            @NotNull @Min(0) Double epsilon,
            @NotNull @Min(0) Double delta,
            @NotNull @Min(0) Double sensitivity,
            @NotNull NoiseMechanism noiseMechanism,
            @NotNull ApplicationStage applicationStage,
            @NotNull @Min(0) Double privacyBudget
    ) {
    }

    public record ConfigResponse(
            Long id,
            Double epsilon,
            Double delta,
            Double sensitivity,
            NoiseMechanism noiseMechanism,
            ApplicationStage applicationStage,
            Double privacyBudget
    ) {
    }

    public record BudgetResponse(
            Double total,
            Double spent,
            Double remaining
    ) {
    }

    public record EventItem(
            Long id,
            PrivacyEventType type,
            Double epsilonSpent,
            Double deltaSpent,
            String note,
            LocalDateTime createdAt
    ) {
    }

    public record ConfigWithBudget(
            ConfigResponse config,
            BudgetResponse budget,
            List<EventItem> recentEvents
    ) {
    }
}
