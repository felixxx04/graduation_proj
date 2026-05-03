package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.dto.response.RecommendationHistoryItem;
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
}
