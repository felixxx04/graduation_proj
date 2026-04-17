package com.medical.service;

import com.medical.dto.request.PrivacyConfigRequest;
import com.medical.entity.PrivacyConfig;
import com.medical.exception.ResourceNotFoundException;
import com.medical.repository.PrivacyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class PrivacyService {
    private final PrivacyRepository privacyRepository;

    public PrivacyConfig getConfig(Long userId) {
        PrivacyConfig config = privacyRepository.findByUserId(userId);
        if (config == null) {
            throw new ResourceNotFoundException("隐私配置不存在: userId=" + userId);
        }
        return config;
    }

    public PrivacyConfig updateConfig(Long userId, PrivacyConfigRequest request) {
        PrivacyConfig config = privacyRepository.findByUserId(userId);
        if (config == null) {
            throw new ResourceNotFoundException("隐私配置不存在: userId=" + userId);
        }
        if (request.getEpsilon() != null) config.setEpsilon(request.getEpsilon());
        if (request.getDelta() != null) config.setDelta(request.getDelta());
        if (request.getSensitivity() != null) config.setSensitivity(request.getSensitivity());
        if (request.getNoiseMechanism() != null) config.setNoiseMechanism(request.getNoiseMechanism());
        if (request.getApplicationStage() != null) config.setApplicationStage(request.getApplicationStage());
        if (request.getPrivacyBudget() != null) config.setPrivacyBudget(request.getPrivacyBudget());
        config.setUserId(userId);
        privacyRepository.update(config);
        return privacyRepository.findByUserId(userId);
    }

    public Map<String, Object> getBudget(Long userId) {
        PrivacyConfig config = privacyRepository.findByUserId(userId);
        if (config == null) {
            throw new ResourceNotFoundException("隐私配置不存在: userId=" + userId);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("total", config.getPrivacyBudget());
        result.put("spent", config.getBudgetUsed());
        result.put("remaining", config.getPrivacyBudget().subtract(config.getBudgetUsed()));
        return result;
    }

    public List<Map<String, Object>> getLedgerEvents(Long userId, int limit) {
        return privacyRepository.findLedgerEventsByUserId(userId, limit);
    }

    public int countLedgerEvents() {
        return privacyRepository.countLedgerEvents();
    }

    public void clearLedger(Long userId) {
        privacyRepository.clearLedgerByUserId(userId);
    }

    public Map<String, Object> getFullPrivacyInfo(Long userId) {
        PrivacyConfig config = privacyRepository.findByUserId(userId);
        if (config == null) {
            throw new ResourceNotFoundException("隐私配置不存在: userId=" + userId);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("config", config);

        Map<String, Object> budget = new HashMap<>();
        budget.put("spent", config.getBudgetUsed());
        budget.put("remaining", config.getPrivacyBudget().subtract(config.getBudgetUsed()));
        result.put("budget", budget);

        result.put("recentEvents", privacyRepository.findLedgerEventsByUserId(userId, 30));

        return result;
    }
}
