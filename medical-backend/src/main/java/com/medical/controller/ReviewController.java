package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.entity.ReviewLog;
import com.medical.repository.ReviewLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/review")
@RequiredArgsConstructor
public class ReviewController {
    private final ReviewLogRepository reviewLogRepository;

    @PostMapping("/log")
    public ApiResponse<Map<String, Object>> submitReview(@RequestBody ReviewLog log) {
        reviewLogRepository.insert(log);
        Map<String, Object> resp = Map.of("id", log.getId());
        return ApiResponse.success(resp);
    }

    @GetMapping("/log/{recommendationId}")
    public ApiResponse<List<ReviewLog>> getReview(@PathVariable String recommendationId) {
        List<ReviewLog> logs = reviewLogRepository.findByRecommendationId(recommendationId);
        return ApiResponse.success(logs);
    }

    @GetMapping("/stats/rejections")
    public ApiResponse<List<Map<String, Object>>> getRejectionStats(
            @RequestParam String startDate,
            @RequestParam String endDate) {
        List<Map<String, Object>> stats = reviewLogRepository.getRejectionStats(startDate, endDate);
        return ApiResponse.success(stats);
    }

    @GetMapping("/stats/modifications")
    public ApiResponse<List<Map<String, Object>>> getModificationStats(
            @RequestParam String startDate,
            @RequestParam String endDate) {
        List<Map<String, Object>> stats = reviewLogRepository.getModificationStats(startDate, endDate);
        return ApiResponse.success(stats);
    }
}
