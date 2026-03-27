package com.grad.medrec.dto;

import jakarta.validation.constraints.Min;

import java.time.LocalDateTime;
import java.util.List;

public final class RecommendationDto {

    private RecommendationDto() {
    }

    public record GenerateRequest(
            Long patientId,
            String age,
            String gender,
            String diseases,
            String symptoms,
            String allergies,
            String currentMedications,
            Boolean dpEnabled,
            @Min(1) Integer topK
    ) {
    }

    public record ExplanationFeature(
            String name,
            double weight,
            double contribution,
            String note
    ) {
    }

    public record Explanation(
            List<ExplanationFeature> features,
            List<String> warnings
    ) {
    }

    public record Item(
            Long drugId,
            String drugName,
            String category,
            String dosage,
            String frequency,
            double confidence,
            double score,
            Double dpNoise,
            String reason,
            List<String> interactions,
            List<String> sideEffects,
            Explanation explanation
    ) {
    }

    public record GenerateResponse(
            Long recommendationId,
            List<Item> selected,
            List<Item> base,
            List<Item> dp,
            boolean dpEnabled
    ) {
    }

    public record HistoryItem(
            Long id,
            Long patientId,
            String patientName,
            boolean dpEnabled,
            Double epsilonUsed,
            LocalDateTime createdAt,
            List<Item> items
    ) {
    }
}
