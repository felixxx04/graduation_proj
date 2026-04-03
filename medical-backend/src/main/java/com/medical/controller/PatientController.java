package com.medical.controller;

import com.medical.dto.request.PatientRequest;
import com.medical.dto.response.ApiResponse;
import com.medical.dto.response.PatientProfile;
import com.medical.service.PatientService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/patients")
@RequiredArgsConstructor
public class PatientController {
    private final PatientService patientService;

    @GetMapping
    public ApiResponse<List<PatientProfile>> getAllPatients() {
        return ApiResponse.success(patientService.getAllPatients());
    }

    @GetMapping("/{id}")
    public ApiResponse<PatientProfile> getPatientById(@PathVariable Long id) {
        PatientProfile patient = patientService.getPatientById(id);
        if (patient == null) {
            return ApiResponse.error("患者不存在");
        }
        return ApiResponse.success(patient);
    }

    @PostMapping
    public ApiResponse<PatientProfile> createPatient(@RequestBody PatientRequest request) {
        return ApiResponse.success("创建成功", patientService.createPatient(request));
    }

    @PutMapping("/{id}")
    public ApiResponse<PatientProfile> updatePatient(@PathVariable Long id, @RequestBody PatientRequest request) {
        PatientProfile updated = patientService.updatePatient(id, request);
        if (updated == null) {
            return ApiResponse.error("患者不存在");
        }
        return ApiResponse.success("更新成功", updated);
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> deletePatient(@PathVariable Long id) {
        patientService.deletePatient(id);
        return ApiResponse.success("删除成功", null);
    }
}
