package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.entity.ReviewLog;
import com.medical.repository.ReviewLogRepository;
import com.medical.security.SecurityUtils;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/review")
@RequiredArgsConstructor
public class ReviewController {
    private final ReviewLogRepository reviewLogRepository;
    private final SecurityUtils securityUtils;

    @PostMapping("/log")
    public ApiResponse<Map<String, Object>> submitReview(@RequestBody ReviewLog log) {
        if (log.getRecommendationId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "推荐ID不能为空");
        }
        if (log.getDoctorDecision() == null
                || !List.of("confirm", "modify", "reject").contains(log.getDoctorDecision())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "审核决策无效，必须为confirm/modify/reject");
        }

        log.setDoctorId(securityUtils.getCurrentUserId());

        reviewLogRepository.insert(log);
        String newStatus = "confirm".equals(log.getDoctorDecision()) ? "confirmed" :
                          "modify".equals(log.getDoctorDecision()) ? "modified" : "rejected";
        reviewLogRepository.updateRecommendationStatus(log.getRecommendationId(), newStatus);
        Map<String, Object> resp = Map.of("id", log.getId(), "reviewStatus", newStatus);
        return ApiResponse.success(resp);
    }

    @GetMapping("/pending")
    public ApiResponse<List<Map<String, Object>>> getPendingReviews() {
        List<Map<String, Object>> pending = reviewLogRepository.findPendingRecommendations();
        return ApiResponse.success(pending);
    }

    @GetMapping("/recommendation/{id}")
    public ApiResponse<Map<String, Object>> getRecommendationDetail(@PathVariable Long id) {
        Map<String, Object> detail = reviewLogRepository.findRecommendationById(id);
        if (detail == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "推荐记录不存在");
        }
        return ApiResponse.success(detail);
    }

    @GetMapping("/log/{recommendationId}")
    public ApiResponse<List<ReviewLog>> getReview(@PathVariable Long recommendationId) {
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
