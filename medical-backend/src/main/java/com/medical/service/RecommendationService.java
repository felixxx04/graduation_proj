package com.medical.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.util.Map;

@Service
public class RecommendationService {
    private final RestTemplate restTemplate = new RestTemplate();
    private final String modelServiceUrl = "http://localhost:8001";
    
    public Map<String, Object> generateRecommendation(Map<String, Object> request) {
        String url = modelServiceUrl + "/model/predict";
        try {
            return restTemplate.postForObject(url, request, Map.class);
        } catch (Exception e) {
            return Map.of("error", "模型服务不可用: " + e.getMessage());
        }
    }
}
