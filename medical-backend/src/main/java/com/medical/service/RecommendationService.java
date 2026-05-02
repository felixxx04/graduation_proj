package com.medical.service;

import com.medical.exception.ModelServiceException;
import com.medical.exception.PrivacyBudgetExhaustedException;
import com.medical.config.ModelServiceConfig;
import com.medical.entity.Drug;
import com.medical.entity.HealthRecord;
import com.medical.entity.Recommendation;
import com.medical.entity.User;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.PrivacyRepository;
import com.medical.repository.UserRepository;
import com.medical.repository.HealthRecordRepository;
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
import java.math.RoundingMode;
import java.util.*;
import java.util.regex.Pattern;

@Service
@RequiredArgsConstructor
@Slf4j
public class RecommendationService {
    private final ModelServiceConfig modelServiceConfig;
    private final DrugService drugService;
    private final RecommendationRepository recommendationRepository;
    private final PrivacyRepository privacyRepository;
    private final UserRepository userRepository;
    private final HealthRecordRepository healthRecordRepository;
    private final ObjectMapper objectMapper;
    private final RestTemplate restTemplate;
    private volatile boolean drugsLoaded = false;

    // 中文→英文性别映射
    private static final Map<String, String> GENDER_MAP = Map.of(
        "男", "MALE",
        "女", "FEMALE",
        "MALE", "MALE",
        "FEMALE", "FEMALE"
    );

    // MySQL ENUM值直接传递（保持完整值以匹配FeatureEncoder词汇表）
    // mild_impairment/moderate_impairment/severe_impairment 同时被 safety_filter 接受
    private static final Map<String, String> RENAL_FUNCTION_MAP = Map.of(
        "normal", "normal",
        "mild_impairment", "mild_impairment",
        "moderate_impairment", "moderate_impairment",
        "severe_impairment", "severe_impairment",
        "unknown", "unknown"
    );

    private static final Map<String, String> HEPATIC_FUNCTION_MAP = Map.of(
        "normal", "normal",
        "mild_impairment", "mild_impairment",
        "moderate_impairment", "moderate_impairment",
        "severe_impairment", "severe_impairment",
        "unknown", "unknown"
    );

    // 妊娠关键词检测模式
    private static final Pattern PREGNANCY_PATTERN = Pattern.compile(
        "妊娠|怀孕|孕期|孕|妊娠期|备孕"
    );

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
            if (drugs.isEmpty()) {
                // 模型服务启动时已从pipeline_data.json加载1815药品
                // MySQL药品表为空时无需发送load-drugs请求
                drugsLoaded = true;
                log.info("No MySQL drugs to load; model service already has pipeline_data drugs");
                return;
            }
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

                Object indicationsParsed = parseJsonToList(drug.getIndications());
                d.put("indications", indicationsParsed);

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

    private Object parseJsonToList(String jsonString) {
        if (jsonString == null || jsonString.isBlank()) {
            return new ArrayList<>();
        }
        try {
            return objectMapper.readValue(jsonString, new TypeReference<List<Object>>() {});
        } catch (Exception e) {
            List<String> singleList = new ArrayList<>();
            singleList.add(jsonString);
            return singleList;
        }
    }

    /**
     * 生成用药推荐：自动补充患者数据 + 字段映射 + 转发到模型服务
     */
    @Transactional
    public Map<String, Object> generateRecommendation(Map<String, Object> request) {
        if (!drugsLoaded) {
            loadDrugsToModelService();
        }

        // 1. 性别映射：中文→英文
        mapGender(request);

        // 2. 药物名称映射：中文→英文通用名
        mapMedicationNames(request);

        // 3. 患者数据自动补充（从DB查询健康档案填充v2字段）
        List<String> dataGaps = enrichPatientData(request);

        String url = modelServiceConfig.getUrl() + "/model/predict";
        Map<String, Object> result;
        try {
            result = restTemplate.postForObject(url, request, Map.class);
        } catch (Exception e) {
            log.error("Model service unavailable: {}", e.getMessage());
            throw new ModelServiceException("模型服务不可用: " + e.getMessage(), e);
        }

        // 4. 将dataGaps添加到响应
        result.put("dataGaps", dataGaps);

        saveRecommendation(request, result);
        return result;
    }

    /**
     * 性别中文→英文映射
     */
    private void mapGender(Map<String, Object> request) {
        Object gender = request.get("gender");
        if (gender != null) {
            String genderStr = gender.toString();
            String mapped = GENDER_MAP.getOrDefault(genderStr, "UNKNOWN");
            request.put("gender", mapped);
            log.debug("Gender mapped: {} -> {}", genderStr, mapped);
        }
    }

    private volatile Map<String, String> cnToEnDrugMap = null;

    /**
     * 药物名称中文→英文映射
     * 利用Drug表的中文名(name)→英文通用名(genericName)做反向查找
     */
    private void mapMedicationNames(Map<String, Object> request) {
        Object medications = request.get("currentMedications");
        if (medications == null) return;

        String medsStr = medications.toString();
        if (medsStr.isBlank()) return;

        // 使用缓存的映射
        Map<String, String> cnToEnMap = buildChineseToEnglishDrugMap();

        // 逐词替换
        String[] medNames = medsStr.split("[，,、;；\\s]+");
        List<String> mappedNames = new ArrayList<>();
        for (String name : medNames) {
            String trimmed = name.trim();
            if (trimmed.isEmpty()) continue;
            String enName = cnToEnMap.getOrDefault(trimmed.toLowerCase(), trimmed);
            mappedNames.add(enName);
        }

        // 以中文逗号重新拼接（模型服务会按逗号分割）
        request.put("currentMedications", String.join("，", mappedNames));
        log.debug("Medications mapped: {} -> {}", medsStr, String.join("，", mappedNames));
    }

    private Map<String, String> buildChineseToEnglishDrugMap() {
        if (cnToEnDrugMap != null) return cnToEnDrugMap;
        List<Drug> allDrugs = drugService.getAllDrugs();
        Map<String, String> map = new HashMap<>();
        for (Drug drug : allDrugs) {
            if (drug.getName() != null && drug.getGenericName() != null) {
                map.put(drug.getName().toLowerCase(), drug.getGenericName());
            }
        }
        cnToEnDrugMap = map;
        return map;
    }

    /**
     * 患者数据自动补充：从DB查询最新健康档案，填充v2字段到请求中
     * 返回缺失字段列表(dataGaps)告知前端
     */
    private List<String> enrichPatientData(Map<String, Object> request) {
        List<String> dataGaps = new ArrayList<>();

        Object patientIdObj = request.get("patientId");
        if (patientIdObj == null) {
            // 匿名模式：无患者ID，尝试从请求height/weight计算BMI
            Object heightObj = request.get("height");
            Object weightObj = request.get("weight");
            boolean bmiComputed = false;
            if (heightObj != null && weightObj != null) {
                try {
                    double heightVal = Double.parseDouble(heightObj.toString());
                    double weightVal = Double.parseDouble(weightObj.toString());
                    if (heightVal > 0 && weightVal > 0) {
                        double heightM = heightVal / 100.0;
                        double bmi = weightVal / (heightM * heightM);
                        request.put("bmi", Math.round(bmi * 100.0) / 100.0);
                        String bmiGroup;
                        if (bmi < 18.5) bmiGroup = "underweight";
                        else if (bmi < 25) bmiGroup = "normal";
                        else if (bmi < 30) bmiGroup = "overweight";
                        else bmiGroup = "obese";
                        request.put("bmi_group", bmiGroup);
                        bmiComputed = true;
                        log.debug("BMI computed from request: height={}, weight={}, bmi={}, group={}", heightVal, weightVal, bmi, bmiGroup);
                    }
                } catch (NumberFormatException e) {
                    log.debug("Failed to parse height/weight for BMI computation");
                }
            }
            // 临床指标始终标记为缺失（只能从DB补充）
            dataGaps.add("肾功能数据");
            dataGaps.add("肝功能数据");
            dataGaps.add("妊娠状态");
            if (!bmiComputed) {
                dataGaps.add("BMI数据");
            }
            return dataGaps;
        }

        Long patientId = Long.valueOf(patientIdObj.toString());
        HealthRecord record = healthRecordRepository.findLatestByPatientId(patientId);
        if (record == null) {
            dataGaps.add("患者健康档案");
            return dataGaps;
        }

        // 肾功能映射
        String renalFunction = record.getRenalFunction();
        if (renalFunction != null && !"unknown".equals(renalFunction)) {
            String mapped = RENAL_FUNCTION_MAP.getOrDefault(renalFunction, "unknown");
            request.put("renal_function", mapped);
            log.debug("Renal function mapped: {} -> {}", renalFunction, mapped);
        } else {
            request.put("renal_function", "unknown");
            dataGaps.add("肾功能数据");
        }

        // 肝功能映射
        String hepaticFunction = record.getHepaticFunction();
        if (hepaticFunction != null && !"unknown".equals(hepaticFunction)) {
            String mapped = HEPATIC_FUNCTION_MAP.getOrDefault(hepaticFunction, "unknown");
            request.put("hepatic_function", mapped);
            log.debug("Hepatic function mapped: {} -> {}", hepaticFunction, mapped);
        } else {
            request.put("hepatic_function", "unknown");
            dataGaps.add("肝功能数据");
        }

        // BMI计算（从height/weight自动推导）
        BigDecimal height = record.getHeight();
        BigDecimal weight = record.getWeight();
        if (height != null && weight != null && height.doubleValue() > 0) {
            double heightM = height.doubleValue() / 100.0;
            double bmi = weight.doubleValue() / (heightM * heightM);
            request.put("bmi", Math.round(bmi * 100.0) / 100.0);
            // BMI分组映射
            String bmiGroup;
            if (bmi < 18.5) bmiGroup = "underweight";
            else if (bmi < 25) bmiGroup = "normal";
            else if (bmi < 30) bmiGroup = "overweight";
            else bmiGroup = "obese";
            request.put("bmi_group", bmiGroup);
        } else {
            dataGaps.add("BMI数据");
        }

        // 妊娠状态推断（从慢性病JSON关键词提取，不从年龄/性别推断）
        String pregnancyStatus = inferPregnancyStatus(record);
        request.put("pregnancy_status", pregnancyStatus);
        if ("unknown".equals(pregnancyStatus)) {
            // 对育龄女性标记可能缺失
            Object genderObj = request.get("gender");
            Object ageObj = request.get("age");
            if ("FEMALE".equals(String.valueOf(genderObj)) && ageObj != null) {
                int age = Integer.parseInt(String.valueOf(ageObj));
                if (age >= 20 && age <= 50) {
                    dataGaps.add("妊娠状态（该患者为育龄女性，建议确认妊娠信息）");
                }
            }
        }

        // 吸烟/饮酒状态
        if (record.getSmokingStatus() != null && !"unknown".equals(record.getSmokingStatus())) {
            request.put("smoking_status", record.getSmokingStatus());
        } else {
            dataGaps.add("吸烟状态");
        }
        if (record.getDrinkingStatus() != null && !"unknown".equals(record.getDrinkingStatus())) {
            request.put("drinking_status", record.getDrinkingStatus());
        } else {
            dataGaps.add("饮酒状态");
        }

        // 血压
        if (record.getBloodPressureSystolic() != null) {
            request.put("blood_pressure_systolic", record.getBloodPressureSystolic());
        } else {
            dataGaps.add("血压数据");
        }

        // 糖尿病相关指标
        if (record.getFastingGlucose() != null) {
            request.put("fasting_glucose", record.getFastingGlucose().doubleValue());
        } else {
            dataGaps.add("空腹血糖");
        }
        if (record.getHba1c() != null) {
            request.put("hba1c", record.getHba1c().doubleValue());
        } else {
            dataGaps.add("糖化血红蛋白");
        }
        if (record.getCholesterolTotal() != null) {
            request.put("cholesterol_total", record.getCholesterolTotal().doubleValue());
        } else {
            dataGaps.add("胆固醇数据");
        }
        if (record.getCholesterolLdl() != null) {
            request.put("cholesterol_ldl", record.getCholesterolLdl().doubleValue());
        }
        if (record.getHeartRate() != null) {
            request.put("heart_rate", record.getHeartRate());
        }

        log.info("Patient data enriched for patientId={}, dataGaps={}", patientId, dataGaps);
        return dataGaps;
    }

    /**
     * 从慢性病JSON关键词推断妊娠状态
     */
    private String inferPregnancyStatus(HealthRecord record) {
        String chronicDiseases = record.getChronicDiseases();
        if (chronicDiseases != null && PREGNANCY_PATTERN.matcher(chronicDiseases).find()) {
            return "pregnant";
        }
        return "unknown";
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