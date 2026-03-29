package com.medical.service;

import com.medical.entity.PrivacyConfig;
import com.medical.repository.PrivacyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class PrivacyService {
    private final PrivacyRepository privacyRepository;
    
    public PrivacyConfig getConfig(Long userId) {
        return privacyRepository.findByUserId(userId);
    }
    
    public PrivacyConfig updateConfig(Long userId, PrivacyConfig config) {
        config.setUserId(userId);
        privacyRepository.update(config);
        return privacyRepository.findByUserId(userId);
    }
    
    public Map<String, Object> getBudget(Long userId) {
        PrivacyConfig config = privacyRepository.findByUserId(userId);
        if (config == null) {
            return null;
        }
        Map<String, Object> result = new HashMap<>();
        result.put("total", config.getPrivacyBudget());
        result.put("spent", config.getBudgetUsed());
        result.put("remaining", config.getPrivacyBudget().subtract(config.getBudgetUsed()));
        return result;
    }
}
