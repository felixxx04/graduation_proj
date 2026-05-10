package com.medical.controller;

import com.medical.dto.request.ClinicalMetricsRequest;
import com.medical.dto.request.PatientRequest;
import com.medical.dto.response.ApiResponse;
import com.medical.dto.response.PatientProfile;
import com.medical.security.SecurityUtils;
import com.medical.service.PatientService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/patients")
@RequiredArgsConstructor
public class PatientController {
    private final PatientService patientService;
    private final SecurityUtils securityUtils;

    @GetMapping
    public ApiResponse<List<PatientProfile>> getAllPatients() {
        return ApiResponse.success(patientService.getAllPatients());
    }

    @GetMapping("/me")
    public ApiResponse<List<PatientProfile>> getMyPatients() {
        Long userId = securityUtils.getCurrentUserId();
        return ApiResponse.success(patientService.getMyPatients(userId));
    }

    @GetMapping("/{id}")
    public ApiResponse<PatientProfile> getPatientById(@PathVariable Long id) {
        return ApiResponse.success(patientService.getPatientById(id));
    }

    @PostMapping
    public ApiResponse<PatientProfile> createPatient(@Valid @RequestBody PatientRequest request) {
        Long userId = "patient".equals(securityUtils.getCurrentUserRole())
            ? securityUtils.getCurrentUserId() : null;
        return ApiResponse.success("创建成功", patientService.createPatient(request, userId));
    }

    @PutMapping("/{id}")
    public ApiResponse<PatientProfile> updatePatient(@PathVariable Long id, @Valid @RequestBody PatientRequest request) {
        return ApiResponse.success("更新成功", patientService.updatePatient(id, request));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> deletePatient(@PathVariable Long id) {
        patientService.deletePatient(id);
        return ApiResponse.success("删除成功", null);
    }

    @PutMapping("/{id}/clinical")
    public ApiResponse<Void> updateClinicalMetrics(
            @PathVariable Long id,
            @RequestBody ClinicalMetricsRequest request) {
        patientService.updateClinicalMetrics(id, request);
        return ApiResponse.success("临床指标更新成功", null);
    }
}
