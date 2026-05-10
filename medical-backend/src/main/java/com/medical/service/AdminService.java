package com.medical.service;

import com.medical.config.ModelServiceConfig;
import com.medical.entity.User;
import com.medical.exception.ModelServiceException;
import com.medical.exception.ResourceNotFoundException;
import com.medical.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;
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
    private final PasswordEncoder passwordEncoder;

    private static final List<String> VALID_ROLES = List.of("admin", "doctor", "patient");

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

    public User createUser(String username, String password, String role) {
        if (username == null || username.isBlank() || username.length() < 2) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "用户名至少2个字符");
        }
        if (password == null || password.length() < 6) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "密码至少6个字符");
        }
        if (!VALID_ROLES.contains(role)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "无效的角色: " + role);
        }
        if (userRepository.findByUsername(username).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "用户名已存在: " + username);
        }

        User user = new User();
        user.setUsername(username);
        user.setPasswordHash(passwordEncoder.encode(password));
        user.setRole(role);
        user.setEnabled(true);
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());
        userRepository.insert(user);
        return user;
    }

    public void deleteUser(Long id, Long currentUserId) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("用户不存在: id=" + id));

        if (user.getId().equals(currentUserId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不能删除自己");
        }

        if ("admin".equals(user.getRole())) {
            int adminCount = userRepository.countByRole("admin");
            if (adminCount <= 1) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不能删除最后一个管理员");
            }
        }

        userRepository.deleteById(id);
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
