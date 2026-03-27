package com.grad.medrec.controller;

import com.grad.medrec.dto.ApiResponse;
import com.grad.medrec.dto.RecommendationDto;
import com.grad.medrec.service.RecommendationService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/recommendations")
public class RecommendationController {

    private final RecommendationService recommendationService;

    public RecommendationController(RecommendationService recommendationService) {
        this.recommendationService = recommendationService;
    }

    @PostMapping("/generate")
    public ApiResponse<RecommendationDto.GenerateResponse> generate(@Valid @RequestBody RecommendationDto.GenerateRequest request) {
        return ApiResponse.ok(recommendationService.generate(request));
    }

    @GetMapping("/history")
    public ApiResponse<List<RecommendationDto.HistoryItem>> history(@RequestParam(defaultValue = "20") int limit) {
        return ApiResponse.ok(recommendationService.history(limit));
    }
}
