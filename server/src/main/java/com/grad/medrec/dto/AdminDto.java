package com.grad.medrec.dto;

import com.grad.medrec.enumtype.TrainingRunStatus;
import com.grad.medrec.enumtype.UserStatus;
import jakarta.validation.constraints.Min;

import java.time.LocalDateTime;
import java.util.List;

public final class AdminDto {

    private AdminDto() {
    }

    public record UserItem(
            Long id,
            String username,
            String role,
            UserStatus status,
            LocalDateTime lastLoginAt
    ) {
    }

    public record UpdateUserStatusRequest(
            UserStatus status
    ) {
    }

    public record StartTrainingRequest(
            @Min(1) Integer epochs
    ) {
    }

    public record TrainingEpochItem(
            Integer epochIndex,
            Double loss,
            Double accuracy,
            Double epsilonSpent,
            LocalDateTime createdAt
    ) {
    }

    public record TrainingRunItem(
            Long id,
            TrainingRunStatus status,
            Integer totalEpochs,
            Double epsilonPerEpoch,
            LocalDateTime startedAt,
            LocalDateTime finishedAt,
            List<TrainingEpochItem> epochs
    ) {
    }

    public record DashboardResponse(
            long patientCount,
            long userCount,
            long recommendationCount,
            long eventCount,
            double spentEpsilon,
            double remainingBudget
    ) {
    }
}
