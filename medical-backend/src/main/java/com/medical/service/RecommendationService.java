package com.medical.service;

import com.medical.exception.ModelServiceException;
import com.medical.exception.PrivacyBudgetExhaustedException;
import com.medical.config.ModelServiceConfig;
import com.medical.entity.Drug;
import com.medical.entity.Recommendation;
import com.medical.entity.User;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.PrivacyRepository;
import com.medical.repository.UserRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.scheduling.annotation.Async;
import org.springframework.transaction.annotation.Transactional;
import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class RecommendationService {
    private final ModelServiceConfig modelServiceConfig;
    private final DrugService drugService;
    private final RecommendationRepository recommendationRepository;
    private final PrivacyRepository privacyRepository;
    private final UserRepository userRepository;
    private final ObjectMapper objectMapper;
    private final RestTemplate restTemplate;
    private volatile boolean drugsLoaded = false;

    @PostConstruct
    public void init() {
        loadDrugsAsync();
    }

    @Async
    public void loadDrugsAsync() {
        try {
            int delayMs = modelServiceConfig.getInitDelayMs();
            log.info("Waiting {}ms for model service to start...", delayMs);
            Thread.sleep(delayMs);
            loadDrugsToModelService();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Drug loading interrupted", e);
        } catch (Exception e) {
            log.error("Failed to load drugs to model service after retry", e);
            drugsLoaded = false;
        }
    }

    private synchronized void loadDrugsToModelService() {
        if (drugsLoaded) return;
        try {
            List<Drug> drugs = drugService.getAllDrugs();
            List<Map<String, Object>> drugData = new ArrayList<>();
            for (Drug drug : drugs) {
                Map<String, Object> d = new HashMap<>();
                d.put("id", drug.getId());
                d.put("generic_name", drug.getGenericName());
                d.put("name", drug.getName());
                d.put("category", drug.getCategory());
                d.put("drug_class_en", drug.getDrugClassEn());
                d.put("pregnancy_category", drug.getPregnancyCategory());
                d.put("is_otc", drug.getIsOtc());
                d.put("rx_otc", drug.getIsOtc());
                d.put("typical_dosage", drug.getTypicalDosage());
                d.put("typical_frequency", drug.getTypicalFrequency());
                d.put("strength", drug.getStrength());

                // indications: 解析JSON字符串为结构化列表
                // 模型侧需要List而非原始字符串
                Object indicationsParsed = parseJsonToList(drug.getIndications());
                d.put("indications", indicationsParsed);

                // contraindications, side_effects, interactions同理解析
                Object contrasParsed = parseJsonToList(drug.getContraindications());
                d.put("contraindications", contrasParsed);

                Object sideEffectsParsed = parseJsonToList(drug.getSideEffects());
                d.put("side_effects", sideEffectsParsed);

                Object interactionsParsed = parseJsonToList(drug.getInteractions());
                d.put("interactions", interactionsParsed);

                drugData.add(d);
            }
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<List<Map<String, Object>>> request = new HttpEntity<>(drugData, headers);
            String url = modelServiceConfig.getUrl() + "/model/load-drugs";
            restTemplate.postForObject(url, request, Map.class);
            drugsLoaded = true;
            log.info("Successfully loaded {} drugs to model service at {}", drugs.size(), modelServiceConfig.getUrl());
        } catch (Exception e) {
            log.error("Error loading drugs to model service: {}", e.getMessage(), e);
            throw new ModelServiceException("Failed to initialize model service", e);
        }
    }

    /**
     * 解析JSON字符串为List — 模型侧需要结构化数据而非原始字符串
     * 如果字符串为null/空/非JSON格式，返回空列表
     */
    private Object parseJsonToList(String jsonString) {
        if (jsonString == null || jsonString.isBlank()) {
            return new ArrayList<>();
        }
        try {
            return objectMapper.readValue(jsonString, new TypeReference<List<Object>>() {});
        } catch (Exception e) {
            // 非JSON格式(纯文本或逗号分隔)，作为单条目列表返回
            List<String> singleList = new ArrayList<>();
            singleList.add(jsonString);
            return singleList;
        }
    }

    @Transactional
    public Map<String, Object> generateRecommendation(Map<String, Object> request) {
        if (!drugsLoaded) {
            loadDrugsToModelService();
        }
        String url = modelServiceConfig.getUrl() + "/model/predict";
        Map<String, Object> result;
        try {
            result = restTemplate.postForObject(url, request, Map.class);
        } catch (Exception e) {
            log.error("Model service unavailable: {}", e.getMessage());
            throw new ModelServiceException("模型服务不可用: " + e.getMessage(), e);
        }
        saveRecommendation(request, result);
        return result;
    }

    private BigDecimal resolveEpsilon(Long userId, Map<String, Object> request) {
        Object epsilon = request.get("epsilon");
        if (epsilon != null) {
            return new BigDecimal(epsilon.toString());
        }
        var config = privacyRepository.findByUserId(userId);
        if (config != null) {
            return config.getEpsilon();
        }
        return new BigDecimal("1.0");
    }

    private void checkPrivacyBudget(Long userId, BigDecimal epsilonUsed) {
        var config = privacyRepository.findByUserId(userId);
        if (config == null) {
            return;
        }
        BigDecimal remaining = config.getPrivacyBudget().subtract(
            config.getBudgetUsed() != null ? config.getBudgetUsed() : BigDecimal.ZERO);
        if (epsilonUsed.compareTo(remaining) > 0) {
            throw new PrivacyBudgetExhaustedException("隐私预算已耗尽，剩余: " + remaining + "，需要: " + epsilonUsed);
        }
    }

    private void saveRecommendation(Map<String, Object> request, Map<String, Object> result) {
        Long userId = getCurrentUserId();
        if (userId == null) {
            log.warn("No authenticated user found, skipping recommendation save");
            return;
        }
        Long patientId = null;
        if (request.containsKey("patientId") && request.get("patientId") != null) {
            patientId = Long.valueOf(request.get("patientId").toString());
        }
        Boolean dpEnabled = (Boolean) request.getOrDefault("dpEnabled", true);
        BigDecimal epsilonUsed = BigDecimal.ZERO;
        if (dpEnabled) {
            epsilonUsed = resolveEpsilon(userId, request);
            checkPrivacyBudget(userId, epsilonUsed);
        }
        Recommendation recommendation = new Recommendation();
        recommendation.setPatientId(patientId);
        recommendation.setUserId(userId);
        recommendation.setInputData(toJson(request));
        recommendation.setResultData(toJson(result));
        recommendation.setDpEnabled(dpEnabled);
        recommendation.setEpsilonUsed(epsilonUsed);
        recommendation.setRecommendationType("realtime");
        recommendationRepository.insert(recommendation);
        if (dpEnabled && epsilonUsed.compareTo(BigDecimal.ZERO) > 0) {
            privacyRepository.addBudgetUsed(userId, epsilonUsed);
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
        if (auth == null || !auth.isAuthenticated()) {
            log.debug("No authentication found in SecurityContext");
            return null;
        }
        String username = auth.getName();
        if (username == null || username.isEmpty()) {
            log.debug("Authentication principal has no username");
            return null;
        }
        Optional<User> userOptional = userRepository.findByUsername(username);
        if (userOptional.isEmpty()) {
            log.error("Authenticated user not found in database: {}", username);
            throw new IllegalStateException("Authenticated user not found: " + username);
        }
        User user = userOptional.get();
        log.debug("Resolved user ID {} for username '{}'", user.getId(), username);
        return user.getId();
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            log.error("Failed to serialize object to JSON: {}", e.getMessage());
            return "{}";
        }
    }
}
