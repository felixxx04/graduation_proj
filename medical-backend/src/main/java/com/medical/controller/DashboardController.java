package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.repository.PatientRepository;
import com.medical.repository.UserRepository;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.PrivacyRepository;
import com.medical.service.AuthService;
import com.medical.entity.User;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {
    private final PatientRepository patientRepository;
    private final UserRepository userRepository;
    private final RecommendationRepository recommendationRepository;
    private final PrivacyRepository privacyRepository;
    private final AuthService authService;

    @GetMapping("/visualization")
    public ApiResponse<Map<String, Object>> getVisualization(@RequestAttribute String username) {
        User user = authService.getCurrentUser(username);
        Long userId = user != null ? user.getId() : null;

        Map<String, Object> data = new HashMap<>();
        data.put("patientCount", patientRepository.findAll().size());
        data.put("userCount", userRepository.findAll().size());
        data.put("recommendationCount", recommendationRepository.countAll());
        data.put("eventCount", privacyRepository.countLedgerEvents());

        // 隐私预算
        if (userId != null) {
            var budgetUsed = privacyRepository.getBudgetUsed(userId);
            var config = privacyRepository.findByUserId(userId);
            data.put("spentEpsilon", budgetUsed != null ? budgetUsed : 0);
            data.put("remainingBudget", config != null ?
                config.getPrivacyBudget().subtract(budgetUsed != null ? budgetUsed : java.math.BigDecimal.ZERO) : 0);
        } else {
            data.put("spentEpsilon", 0);
            data.put("remainingBudget", 0);
        }

        return ApiResponse.success(data);
    }
}
