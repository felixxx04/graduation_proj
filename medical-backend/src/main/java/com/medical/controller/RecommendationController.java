package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.dto.response.RecommendationHistoryItem;
import com.medical.entity.User;
import com.medical.repository.UserRepository;
import com.medical.service.RecommendationService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/recommendations")
@RequiredArgsConstructor
public class RecommendationController {
    private final RecommendationService recommendationService;
    private final UserRepository userRepository;

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
        Long userId = getCurrentUserId();
        return ApiResponse.success(recommendationService.getHistoryByUserId(userId));
    }

    private Long getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated()) return null;
        String username = auth.getName();
        Optional<User> userOpt = userRepository.findByUsername(username);
        return userOpt.map(User::getId).orElse(null);
    }
}
