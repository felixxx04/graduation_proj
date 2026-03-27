package com.grad.medrec.controller;

import com.grad.medrec.dto.ApiResponse;
import com.grad.medrec.dto.PrivacyDto;
import com.grad.medrec.service.PrivacyService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/privacy")
public class PrivacyController {

    private final PrivacyService privacyService;

    public PrivacyController(PrivacyService privacyService) {
        this.privacyService = privacyService;
    }

    @GetMapping("/config")
    public ApiResponse<PrivacyDto.ConfigWithBudget> getConfig() {
        return ApiResponse.ok(privacyService.getConfigWithBudget());
    }

    @PutMapping("/config")
    public ApiResponse<PrivacyDto.ConfigResponse> updateConfig(@Valid @RequestBody PrivacyDto.ConfigRequest request) {
        return ApiResponse.ok("updated", privacyService.updateConfig(request));
    }

    @GetMapping("/events")
    public ApiResponse<List<PrivacyDto.EventItem>> listEvents(@RequestParam(defaultValue = "100") int limit) {
        return ApiResponse.ok(privacyService.listEvents(limit));
    }

    @DeleteMapping("/events")
    public ApiResponse<Void> clearEvents() {
        privacyService.clearEvents();
        return ApiResponse.ok("cleared");
    }
}
