package com.grad.medrec.controller;

import com.grad.medrec.dto.ApiResponse;
import com.grad.medrec.dto.PatientDto;
import com.grad.medrec.service.PatientService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/patients")
public class PatientController {

    private final PatientService patientService;

    public PatientController(PatientService patientService) {
        this.patientService = patientService;
    }

    @GetMapping
    public ApiResponse<List<PatientDto.Item>> list() {
        return ApiResponse.ok(patientService.list());
    }

    @PostMapping
    public ApiResponse<PatientDto.Item> create(@Valid @RequestBody PatientDto.UpsertRequest request) {
        return ApiResponse.ok("created", patientService.create(request));
    }

    @PutMapping("/{id}")
    public ApiResponse<PatientDto.Item> update(@PathVariable Long id, @Valid @RequestBody PatientDto.UpsertRequest request) {
        return ApiResponse.ok("updated", patientService.update(id, request));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        patientService.delete(id);
        return ApiResponse.ok("deleted");
    }
}
