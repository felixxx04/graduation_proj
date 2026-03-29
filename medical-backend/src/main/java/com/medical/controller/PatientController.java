package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.entity.Patient;
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
    public ApiResponse<List<Patient>> getAllPatients() {
        return ApiResponse.success(patientService.getAllPatients());
    }
    
    @GetMapping("/{id}")
    public ApiResponse<Patient> getPatientById(@PathVariable Long id) {
        Patient patient = patientService.getPatientById(id);
        if (patient == null) {
            return ApiResponse.error("患者不存在");
        }
        return ApiResponse.success(patient);
    }
    
    @PostMapping
    public ApiResponse<Patient> createPatient(@RequestBody Patient patient) {
        return ApiResponse.success("创建成功", patientService.createPatient(patient));
    }
    
    @PutMapping("/{id}")
    public ApiResponse<Patient> updatePatient(@PathVariable Long id, @RequestBody Patient patient) {
        patient.setId(id);
        Patient updated = patientService.updatePatient(patient);
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
