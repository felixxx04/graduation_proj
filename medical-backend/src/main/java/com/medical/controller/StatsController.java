package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.repository.RecommendationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {
    private final RecommendationRepository recommendationRepository;

    @GetMapping("/recommendations")
    public ApiResponse<Map<String, Object>> getRecommendationStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalRecommendations", recommendationRepository.count());
        List<Map<String, Object>> statusList = recommendationRepository.countByStatus();
        Map<String, Object> statusMap = new HashMap<>();
        for (Map<String, Object> row : statusList) {
            String status = String.valueOf(row.getOrDefault("review_status", "unknown"));
            Object cnt = row.get("cnt");
            long count = cnt instanceof Number ? ((Number) cnt).longValue() : 0L;
            statusMap.put(status, count);
        }
        stats.put("statusDistribution", statusMap);
        return ApiResponse.success(stats);
    }
}
