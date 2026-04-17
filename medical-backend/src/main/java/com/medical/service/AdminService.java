package com.medical.service;

import com.medical.config.ModelServiceConfig;
import com.medical.entity.User;
import com.medical.exception.ModelServiceException;
import com.medical.exception.ResourceNotFoundException;
import com.medical.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class AdminService {
    private final UserRepository userRepository;
    private final ModelServiceConfig modelServiceConfig;
    private final RestTemplate restTemplate;

    public List<User> getAllUsers() {
        return userRepository.findAll();
    }

    public User updateUserStatus(Long id, Boolean enabled) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("用户不存在: id=" + id));
        user.setEnabled(enabled);
        user.setUpdatedAt(LocalDateTime.now());
        userRepository.update(user);
        return user;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> startTraining(int epochs) {
        Map<String, Object> trainRequest = new HashMap<>();
        trainRequest.put("epochs", epochs);
        trainRequest.put("learningRate", 0.01);
        trainRequest.put("dpEnabled", true);
        trainRequest.put("epsilon", 1.0);
        trainRequest.put("batchSize", 32);

        String url = modelServiceConfig.getUrl() + "/model/train";
        Map<String, Object> result;
        try {
            result = restTemplate.postForObject(url, trainRequest, Map.class);
        } catch (Exception e) {
            throw new ModelServiceException("训练请求失败: " + e.getMessage(), e);
        }

        if (result == null) {
            throw new ModelServiceException("模型服务返回空响应");
        }

        return result;
    }
}
