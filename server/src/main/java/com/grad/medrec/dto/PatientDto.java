package com.grad.medrec.dto;

import com.grad.medrec.enumtype.PatientGender;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;
import java.util.List;

public final class PatientDto {

    private PatientDto() {
    }

    public record UpsertRequest(
            @NotBlank String name,
            @NotNull @Min(0) @Max(130) Integer age,
            @NotNull PatientGender gender,
            @NotNull @Min(0) Double height,
            @NotNull @Min(0) Double weight,
            List<String> allergies,
            List<String> chronicDiseases,
            List<String> currentMedications,
            String medicalHistory
    ) {
    }

    public record Item(
            Long id,
            String name,
            Integer age,
            PatientGender gender,
            Double height,
            Double weight,
            List<String> allergies,
            List<String> chronicDiseases,
            List<String> currentMedications,
            String medicalHistory,
            LocalDateTime createdAt
    ) {
    }
}
