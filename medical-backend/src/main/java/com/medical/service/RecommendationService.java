package com.medical.service;

import com.medical.entity.Drug;
import com.medical.entity.Recommendation;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.PrivacyRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.ArrayList;

@Service
@RequiredArgsConstructor
public class RecommendationService {
    private final RestTemplate restTemplate = new RestTemplate();
    private final String modelServiceUrl = "http://localhost:8001";
    private final DrugService drugService;
    private final RecommendationRepository recommendationRepository;
    private final PrivacyRepository privacyRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private boolean drugsLoaded = false;

    @PostConstruct
    public void init() {
        // 启动时异步加载药物数据到模型服务
        new Thread(() -> {
            try {
                Thread.sleep(2000); // 等待模型服务启动
                loadDrugsToModelService();
            } catch (Exception e) {
                System.err.println("Failed to load drugs to model service: " + e.getMessage());
            }
        }).start();
    }

    private synchronized void loadDrugsToModelService() {
        if (drugsLoaded) return;

        try {
            List<Drug> drugs = drugService.getAllDrugs();
            List<Map<String, Object>> drugData = new ArrayList<>();

            for (Drug drug : drugs) {
                Map<String, Object> d = new HashMap<>();
                d.put("id", drug.getId());
                d.put("name", drug.getName());
                d.put("category", drug.getCategory());
                d.put("indications", drug.getIndications());
                d.put("contraindications", drug.getContraindications());
                d.put("side_effects", drug.getSideEffects());
                d.put("interactions", drug.getInteractions());
                d.put("typical_dosage", drug.getTypicalDosage());
                d.put("typical_frequency", drug.getTypicalFrequency());
                drugData.add(d);
            }

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<List<Map<String, Object>>> request = new HttpEntity<>(drugData, headers);

            restTemplate.postForObject(modelServiceUrl + "/model/load-drugs", request, Map.class);
            drugsLoaded = true;
            System.out.println("Loaded " + drugs.size() + " drugs to model service");
        } catch (Exception e) {
            System.err.println("Error loading drugs to model service: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> generateRecommendation(Map<String, Object> request) {
        // 确保药物数据已加载
        if (!drugsLoaded) {
            loadDrugsToModelService();
        }

        String url = modelServiceUrl + "/model/predict";
        Map<String, Object> result;

        try {
            result = restTemplate.postForObject(url, request, Map.class);
        } catch (Exception e) {
            return Map.of("error", "模型服务不可用: " + e.getMessage());
        }

        // 保存推荐记录到数据库
        try {
            saveRecommendation(request, result);
        } catch (Exception e) {
            System.err.println("Failed to save recommendation: " + e.getMessage());
        }

        return result;
    }

    private void saveRecommendation(Map<String, Object> request, Map<String, Object> result) {
        // 获取当前用户ID
        Long userId = getCurrentUserId();
        if (userId == null) return;

        // 获取患者ID
        Long patientId = null;
        if (request.containsKey("patientId") && request.get("patientId") != null) {
            patientId = Long.valueOf(request.get("patientId").toString());
        }

        // 检查是否启用差分隐私
        Boolean dpEnabled = (Boolean) request.getOrDefault("dpEnabled", true);

        // 获取隐私参数
        BigDecimal epsilonUsed = BigDecimal.ZERO;
        if (dpEnabled) {
            Object epsilon = request.get("epsilon");
            if (epsilon == null) {
                // 从隐私配置获取默认值
                var config = privacyRepository.findByUserId(userId);
                if (config != null) {
                    epsilonUsed = config.getEpsilon();
                } else {
                    epsilonUsed = new BigDecimal("0.1"); // 默认值
                }
            } else {
                epsilonUsed = new BigDecimal(epsilon.toString());
            }
        }

        // 保存推荐记录
        Recommendation recommendation = new Recommendation();
        recommendation.setPatientId(patientId);
        recommendation.setUserId(userId);
        recommendation.setInputData(toJson(request));
        recommendation.setResultData(toJson(result));
        recommendation.setDpEnabled(dpEnabled);
        recommendation.setEpsilonUsed(epsilonUsed);
        recommendation.setRecommendationType("realtime");

        recommendationRepository.insert(recommendation);

        // 记录隐私预算消耗
        if (dpEnabled && epsilonUsed.compareTo(BigDecimal.ZERO) > 0) {
            // 更新已使用预算
            privacyRepository.addBudgetUsed(userId, epsilonUsed);

            // 记录到隐私账本
            Map<String, Object> ledgerParams = new HashMap<>();
            ledgerParams.put("userId", userId);
            ledgerParams.put("eventType", "recommendation");
            ledgerParams.put("epsilonSpent", epsilonUsed);
            ledgerParams.put("deltaSpent", BigDecimal.ZERO);
            ledgerParams.put("noiseMechanism", "laplace");
            ledgerParams.put("note", "推荐ID: " + recommendation.getId());
            privacyRepository.insertLedgerEvent(ledgerParams);
        }
    }

    private Long getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated()) {
            // 假设用户名存储在principal中
            String username = auth.getName();
            // 需要从UserRepository获取用户ID
            // 这里简化处理，返回1L（admin用户）
            return 1L; // 实际应该根据username查询
        }
        return null;
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            return "{}";
        }
    }
}
