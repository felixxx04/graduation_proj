package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.dto.response.RecommendationHistoryItem;
import com.medical.security.SecurityUtils;
import com.medical.service.RecommendationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/recommendations")
@RequiredArgsConstructor
public class RecommendationController {
    private final RecommendationService recommendationService;
    private final SecurityUtils securityUtils;

    @PostMapping("/generate")
    public ApiResponse<Map<String, Object>> generate(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(recommendationService.generateRecommendation(request));
    }

    @GetMapping
    public ApiResponse<List<RecommendationHistoryItem>> getHistory(
            @RequestParam(required = false) Long patientId) {
        if (patientId != null) {
            return ApiResponse.success(recommendationService.getHistoryByPatientId(patientId));
        }
        return ApiResponse.success(recommendationService.getAllHistory());
    }

    @GetMapping("/my-history")
    public ApiResponse<List<RecommendationHistoryItem>> getMyHistory() {
        Long userId = securityUtils.getCurrentUserId();
        return ApiResponse.success(recommendationService.getHistoryByUserId(userId));
    }
}
