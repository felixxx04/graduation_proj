package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.repository.RecommendationRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {
    private final RecommendationRepository recommendationRepository;
    private final ObjectMapper objectMapper;

    @GetMapping("/recommendations")
    public ApiResponse<Map<String, Object>> getRecommendationStats() {
        Map<String, Object> stats = new HashMap<>();

        // 基本统计
        stats.put("totalRecommendations", recommendationRepository.count());

        // 审核状态分布
        List<Map<String, Object>> statusList = recommendationRepository.countByStatus();
        Map<String, Object> statusMap = new LinkedHashMap<>();
        for (Map<String, Object> row : statusList) {
            String status = String.valueOf(row.getOrDefault("review_status", "unknown"));
            Object cnt = row.get("cnt");
            long count = cnt instanceof Number ? ((Number) cnt).longValue() : 0L;
            statusMap.put(status, count);
        }
        stats.put("statusDistribution", statusMap);

        // 审核通过率
        Map<String, Object> approval = recommendationRepository.approvalStats();
        if (approval != null) {
            long total = toLong(approval.get("total"));
            long confirmed = toLong(approval.get("confirmed"));
            stats.put("approvalTotal", total);
            stats.put("approvalConfirmed", confirmed);
            stats.put("approvalRate", total > 0 ? Math.round(confirmed * 1000.0 / total) / 10.0 : 0);
        }

        // 每日推荐趋势
        List<Map<String, Object>> dailyData = recommendationRepository.countByDay();
        stats.put("trend", dailyData.stream().map(row -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("day", row.get("day"));
            m.put("count", row.get("cnt"));
            return m;
        }).collect(Collectors.toList()));

        // 药物分析：从 result_data JSON 提取药物名和分类
        List<String> resultDataList = recommendationRepository.findAllResultData();
        Map<String, Integer> drugCounts = new LinkedHashMap<>();
        Map<String, Integer> categoryCounts = new LinkedHashMap<>();
        Set<String> uniqueDrugs = new LinkedHashSet<>();

        for (String json : resultDataList) {
            try {
                Map<String, Object> result = objectMapper.readValue(json, Map.class);
                Object selected = result.get("selected");
                if (selected instanceof List) {
                    for (Object item : (List<?>) selected) {
                        if (item instanceof Map) {
                            Map<?, ?> drug = (Map<?, ?>) item;
                            String name = String.valueOf(drug.getOrDefault("drugName", ""));
                            String category = String.valueOf(drug.getOrDefault("category", ""));
                            if (!name.isEmpty() && !"null".equals(name)) {
                                drugCounts.merge(name, 1, Integer::sum);
                                uniqueDrugs.add(name);
                                if (!category.isEmpty() && !"null".equals(category)) {
                                    categoryCounts.merge(category, 1, Integer::sum);
                                }
                            }
                        }
                    }
                }
            } catch (Exception ignored) {
                // Skip malformed JSON
            }
        }

        // Top 10 药物
        List<Map<String, Object>> topDrugs = drugCounts.entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .limit(10)
            .map(e -> {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("name", e.getKey());
                m.put("count", e.getValue());
                return m;
            })
            .collect(Collectors.toList());
        stats.put("topDrugs", topDrugs);

        // 药物分类分布
        List<Map<String, Object>> categories = categoryCounts.entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .map(e -> {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("name", e.getKey());
                m.put("value", e.getValue());
                return m;
            })
            .collect(Collectors.toList());
        stats.put("categoryDistribution", categories);
        stats.put("uniqueDrugCount", uniqueDrugs.size());

        return ApiResponse.success(stats);
    }

    private long toLong(Object obj) {
        if (obj instanceof Number) return ((Number) obj).longValue();
        if (obj instanceof String) return Long.parseLong((String) obj);
        return 0;
    }
}
