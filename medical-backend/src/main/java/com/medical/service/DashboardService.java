package com.medical.service;

import com.medical.repository.PatientRepository;
import com.medical.repository.PrivacyRepository;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class DashboardService {
    private final PatientRepository patientRepository;
    private final UserRepository userRepository;
    private final RecommendationRepository recommendationRepository;
    private final PrivacyRepository privacyRepository;

    public Map<String, Object> getVisualization(Long userId) {
        Map<String, Object> data = new HashMap<>();
        data.put("patientCount", patientRepository.findAll().size());
        data.put("userCount", userRepository.findAll().size());
        data.put("recommendationCount", recommendationRepository.countAll());
        data.put("eventCount", privacyRepository.countLedgerEvents());

        if (userId != null) {
            BigDecimal budgetUsed = privacyRepository.getBudgetUsed(userId);
            var config = privacyRepository.findByUserId(userId);
            data.put("spentEpsilon", budgetUsed != null ? budgetUsed : BigDecimal.ZERO);
            data.put("remainingBudget", config != null ?
                config.getPrivacyBudget().subtract(budgetUsed != null ? budgetUsed : BigDecimal.ZERO) : BigDecimal.ZERO);
        } else {
            data.put("spentEpsilon", BigDecimal.ZERO);
            data.put("remainingBudget", BigDecimal.ZERO);
        }

        return data;
    }
}
