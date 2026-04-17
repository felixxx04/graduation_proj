package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.service.RecommendationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
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
}
